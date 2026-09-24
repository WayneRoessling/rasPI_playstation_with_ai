"""Offline tests for voice_pipeline's latency paths (no audio hardware, no Ollama).

Covers end-of-speech detection on synthetic PCM (auto and manual
sensitivity, saved panel settings), sentence regrouping of
streamed LLM text, parsing Ollama's streaming response, the streaming
request payload, and the speak-while-generating worker.

Run::

    python tests/test_voice_pipeline.py

Standalone script (like overlay/scenario/test_ptt_smoke.py): prints PASS or
exits non-zero.
"""

from __future__ import annotations

import io
import json
import math
import struct
import sys
import threading
import time
import types
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# voice_pipeline imports cv2 for vision; not needed here.
sys.modules.setdefault("cv2", types.SimpleNamespace())

import voice_pipeline as vp  # noqa: E402

FRAME_SAMPLES = vp.VAD_FRAME_BYTES // 2


def _frames(seconds: float, amplitude: float) -> list[bytes]:
    """Sine-tone (or near-silence) frames at 16 kHz, 30 ms each."""
    out = []
    for f in range(int(seconds * 1000 / vp.VAD_FRAME_MS)):
        samples = [
            int(amplitude * math.sin(2 * math.pi * 220 * (f * FRAME_SAMPLES + i) / vp.VAD_RATE))
            for i in range(FRAME_SAMPLES)
        ]
        out.append(struct.pack(f"<{FRAME_SAMPLES}h", *samples))
    return out


def _secs(pcm: bytes) -> float:
    return len(pcm) / 2 / vp.VAD_RATE


def test_vad_utterance():
    """Quiet room, 1 s of speech, silence: ends ~0.8 s after speech stops."""
    frames = _frames(0.5, 50) + _frames(1.0, 5000) + _frames(3.0, 50)
    pcm = vp._vad_segment(iter(frames), silence_ms=800)
    assert pcm is not None, "speech not detected"
    # pre-roll (0.3) + speech (1.0) + trailing silence (0.8), frame-rounded
    assert 1.9 <= _secs(pcm) <= 2.3, f"utterance length {_secs(pcm):.2f}s"
    print(f"  vad_utterance:   OK  ({_secs(pcm):.2f}s captured)")


def test_vad_no_speech():
    """Nobody talks: gives up after the listen window instead of recording forever."""
    consumed = 0

    def counting(frames):
        nonlocal consumed
        for f in frames:
            consumed += 1
            yield f

    pcm = vp._vad_segment(counting(_frames(15.0, 50)), listen_secs=10)
    assert pcm is None, "silence reported as speech"
    assert consumed * vp.VAD_FRAME_MS <= 10_100, f"read {consumed} frames"
    print("  vad_no_speech:   OK")


def test_vad_max_length():
    """Never-ending speech is capped at max_secs."""
    pcm = vp._vad_segment(iter(_frames(0.3, 50) + _frames(20.0, 5000)), max_secs=5)
    assert pcm is not None and 5.0 <= _secs(pcm) <= 5.5, f"{_secs(pcm) if pcm else None}"
    print("  vad_max_length:  OK")


def test_vad_talk_during_calibration():
    """Speaking from the first frame still works (threshold is capped)."""
    pcm = vp._vad_segment(iter(_frames(1.5, 5000) + _frames(2.0, 50)))
    assert pcm is not None, "speech during calibration was missed"
    print("  vad_calibration: OK")


def test_vad_manual_threshold_and_levels():
    """A manual threshold replaces calibration; on_level sees every frame."""
    loud = _frames(0.3, 50) + _frames(1.0, 5000) + _frames(1.5, 50)   # tone RMS ~3500
    assert vp._vad_segment(iter(loud), fixed_threshold=3900) is None, "too-high threshold still triggered"
    levels: list[tuple[float, float]] = []
    pcm = vp._vad_segment(iter(loud), fixed_threshold=1000, on_level=lambda r, t: levels.append((r, t)))
    assert pcm is not None
    assert levels and all(t == 1000 for _, t in levels), "threshold not reported"
    assert max(r for r, _ in levels) > 3000 and min(r for r, _ in levels) < 100
    print("  vad_manual:      OK")


def test_vad_settings_persist():
    """Panel settings round-trip through the config file and clamp to range."""
    import os
    import tempfile
    import mini_ai_config as cfg

    with tempfile.TemporaryDirectory() as d, \
         mock.patch.object(cfg, "CONFIG_DIR", d), \
         mock.patch.object(cfg, "CONFIG_PATH", str(Path(d) / "config.json")), \
         mock.patch.dict(os.environ):   # restored on exit
        os.environ.pop("MINI_AI_VAD_THRESHOLD", None)
        os.environ.pop("MINI_AI_VAD_SILENCE_MS", None)
        assert (cfg.load_vad_threshold(), cfg.load_vad_silence_ms()) == (0.0, 800)   # defaults: auto
        cfg.save_vad_threshold(1234)
        cfg.save_vad_silence_ms(99999)
        assert (cfg.load_vad_threshold(), cfg.load_vad_silence_ms()) == (1234.0, cfg.MAX_VAD_SILENCE_MS)
        cfg.save_vad_threshold(0)
        assert cfg.load_vad_threshold() == 0.0
        os.environ["MINI_AI_VAD_SILENCE_MS"] = "500"
        assert cfg.load_vad_silence_ms() == 500, "env override ignored"
    state = vp.RuntimeState("t", "v", voice=object(), volume_gain=1.0, personality=object())
    state.set_vad_threshold(900)
    state.set_vad_silence_ms(1200)
    assert state.vad_settings() == (900, 1200)
    print("  vad_settings:    OK")


class FakeArecord:
    """Popen stand-in whose stdout replays canned PCM, then hits EOF."""

    def __init__(self, pcm: bytes):
        self.stdout = io.BytesIO(pcm)
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 1
        return self.returncode


def test_record_until_silence():
    """WAV comes out 16 kHz mono; arecord dying mid-listen is an error, not silence."""
    import os
    import wave

    speech = b"".join(_frames(0.5, 50) + _frames(1.0, 5000) + _frames(1.5, 50))
    with mock.patch.object(vp, "_get_audio_card", return_value="plughw:CARD=Test,DEV=0"), \
         mock.patch.object(vp.subprocess, "Popen", return_value=FakeArecord(speech)):
        path = vp.record_until_silence()
    try:
        with wave.open(path) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
            assert 1.9 <= w.getnframes() / 16000 <= 2.3
    finally:
        os.unlink(path)

    with mock.patch.object(vp, "_get_audio_card", return_value="plughw:CARD=Test,DEV=0"), \
         mock.patch.object(vp.subprocess, "Popen", return_value=FakeArecord(b"\0" * 3200)):
        try:
            vp.record_until_silence()
        except RuntimeError as e:
            assert "arecord stopped" in str(e)
        else:
            raise AssertionError("arecord EOF not reported")
    print("  record_wav:      OK")


def test_sentences():
    pieces = ["Hello there", ", how are", " you today? I am", " fine. Ok.", " Bye now"]
    got = list(vp._sentences(pieces))
    assert got == ["Hello there, how are you today?", "I am fine. Ok. Bye now"], got
    assert list(vp._sentences(["One line\n", "Second line"], min_chars=5)) == ["One line", "Second line"]
    print("  sentences:       OK")


def test_chat_stream_parsing():
    lines = [
        {"message": {"content": "Hi"}, "done": False},
        {"message": {"content": " there."}, "done": False},
        {"message": {"content": ""}, "done": True},
    ]
    body = io.BytesIO(b"".join(json.dumps(x).encode() + b"\n" for x in lines))
    assert "".join(vp._iter_chat_stream(body)) == "Hi there."

    body = io.BytesIO(json.dumps({"error": "model not found"}).encode() + b"\n")
    try:
        list(vp._iter_chat_stream(body))
    except RuntimeError as e:
        assert "model not found" in str(e)
    else:
        raise AssertionError("Ollama error not raised")
    print("  chat_stream:     OK")


def test_stream_request_payload():
    sent = {}

    def fake_urlopen(req, timeout):
        sent.update(json.loads(req.data), url=req.full_url, timeout=timeout)
        return io.BytesIO(json.dumps({"message": {"content": "ok"}, "done": True}).encode())

    with mock.patch.object(vp.urllib.request, "urlopen", fake_urlopen):
        assert vp.ask_llm("hi", "text-m", "vision-m", system_prompt="be brief") == "ok"
    assert sent["url"].endswith("/api/chat") and sent["model"] == "text-m"
    assert sent["stream"] is True and sent["keep_alive"] == vp.KEEP_ALIVE
    assert sent["messages"][0] == {"role": "system", "content": "be brief"}
    print("  stream_payload:  OK")


def test_speak_streamed():
    """First sentence is spoken while later ones are still being generated."""
    state = vp.RuntimeState("t", "v", voice=object(), volume_gain=1.0, personality=object())
    spoken: list[tuple[str, float]] = []
    first_spoken = threading.Event()

    def fake_speak(text, voice, gain):
        spoken.append((text, time.monotonic()))
        first_spoken.set()

    def slow_llm():
        yield "First sentence."
        assert first_spoken.wait(2.0), "nothing spoken while generation continued"
        yield "Second sentence."

    with mock.patch.object(vp, "speak", fake_speak):
        full = vp._speak_streamed(slow_llm(), state, status_q=None)
    assert [s for s, _ in spoken] == ["First sentence.", "Second sentence."], spoken
    assert full == "First sentence. Second sentence."

    def failing_speak(text, voice, gain):
        raise RuntimeError("aplay: device busy")

    with mock.patch.object(vp, "speak", failing_speak):
        try:
            vp._speak_streamed(iter(["A sentence."]), state, status_q=None)
        except RuntimeError as e:
            assert "device busy" in str(e)
        else:
            raise AssertionError("playback error swallowed")
    print("  speak_streamed:  OK")


def main() -> int:
    print("voice_pipeline latency tests")
    try:
        test_vad_utterance()
        test_vad_no_speech()
        test_vad_max_length()
        test_vad_talk_during_calibration()
        test_vad_manual_threshold_and_levels()
        test_vad_settings_persist()
        test_record_until_silence()
        test_sentences()
        test_chat_stream_parsing()
        test_stream_request_payload()
        test_speak_streamed()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
