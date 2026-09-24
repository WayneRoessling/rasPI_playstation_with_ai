#!/usr/bin/env python3
"""
Mini-AI Voice Pipeline
Voice-in -> Whisper STT -> Ollama LLM -> Piper TTS -> Speaker
Vision: USB camera -> OpenCV -> Vision LLM -> Piper TTS -> Speaker

The pipeline can run in two modes:

  1. Headless CLI loop  -- `python voice_pipeline.py`
     Loads config from disk once, prints to stdout, no GUI.

  2. Embedded in the Tk control panel -- mini_ai_panel.py imports
     run_loop() and starts it in a daemon thread, passing in a
     RuntimeState that can be mutated live (voice/volume) from
     widget callbacks.

Active text/vision models, voice, and volume_gain come from
mini_ai_config (~/.config/mini-ai/config.json) on first load. The
RuntimeState lets the GUI override them at runtime without restart.
"""
from __future__ import annotations

import sys
import subprocess
import tempfile
import os
import re
import base64
import json
import threading
import traceback
import urllib.request
import wave
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from queue import Queue

import cv2

# Make sibling modules importable when launched from anywhere
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mini_ai_config import (
    Voice,
    Personality,
    load_preset,
    load_voice,
    load_volume_gain,
    load_personality,
    load_scenario,
    load_vad_silence_ms,
    load_vad_threshold,
    voice_model_path,
)

HOME = os.path.expanduser("~")
WHISPER_BIN = os.path.join(HOME, "whisper.cpp/build/bin/whisper-cli")
WHISPER_MODEL = os.path.join(HOME, "whisper.cpp/models/ggml-base.en.bin")
PIPER_BIN = os.path.join(HOME, "mini-ai/.venv/bin/piper")
OLLAMA_URL = "http://localhost:11434/api"
CAMERA_INDEX = 0

# ── Overlay integration (Drop 3) ──────────────────────────────────────────────
#
# When MINI_AI_OVERLAY=true, the loop swaps the fixed-duration arecord and the
# direct Ollama call for the scenario-driven tool-use pipeline: PTT-gated
# recording, HAL state in the system prompt, LLM tool calls executed against
# the simulator (or, later, the RP2040 firmware). Default off — the existing
# voice loop continues to work for users without the overlay hardware/sim.
#
# The mode (plain assistant vs. which scenario) is live state, picked in the
# control panel and saved in config.json. Env knobs:
#   MINI_AI_OVERLAY=true|false      force a scenario / the plain assistant at startup
#   MINI_AI_OVERLAY_SCENARIO=<id>   scenario for MINI_AI_OVERLAY=true; default
#                                   space_command_launch
#   MINI_AI_OVERLAY_HAL=<spec>      HAL endpoint; default ws://127.0.0.1:8765/hal (the
#                                   simulator). serial:auto = the real RP2040 panel over
#                                   USB, found by vendor id; serial:/dev/ttyACM0 = a
#                                   specific port
#   MINI_AI_OVERLAY_MODEL=<name>    Ollama model; default qwen2.5:14b
OVERLAY_HAL_URL = os.environ.get("MINI_AI_OVERLAY_HAL", "ws://127.0.0.1:8765/hal")
OVERLAY_MODEL = os.environ.get("MINI_AI_OVERLAY_MODEL", "qwen2.5:14b")
OVERLAY_PTT_MAX_SECS = int(os.environ.get("MINI_AI_OVERLAY_PTT_MAX", "30"))

# ── Latency knobs ─────────────────────────────────────────────────────────────
#   MINI_AI_KEEP_ALIVE=<dur>        how long Ollama keeps a model loaded after a
#                                   request (Ollama's own default is 5m)
#   MINI_AI_VAD=0                   disable end-of-speech detection and record a
#                                   fixed 10s window instead
#   MINI_AI_MAX_UTTERANCE=<secs>    hard cap on one utterance
# Mic sensitivity (speech threshold, 0 = auto) and the pause that ends an
# utterance are live settings in RuntimeState — adjustable in the control
# panel and saved via mini_ai_config (env MINI_AI_VAD_THRESHOLD /
# MINI_AI_VAD_SILENCE_MS override the saved values).
KEEP_ALIVE = os.environ.get("MINI_AI_KEEP_ALIVE", "30m")
VAD_ENABLED = os.environ.get("MINI_AI_VAD", "1").lower() not in ("0", "false", "no")
MAX_UTTERANCE_SECS = int(os.environ.get("MINI_AI_MAX_UTTERANCE", "15"))
LISTEN_WINDOW_SECS = 10       # wait this long for speech to start, then listen again

VAD_RATE = 16000              # record straight at Whisper's rate: no resample step
VAD_FRAME_MS = 30
VAD_FRAME_BYTES = VAD_RATE * VAD_FRAME_MS // 1000 * 2    # 16-bit mono
VAD_CALIBRATE_MS = 300        # opening window used to measure room noise
VAD_NOISE_FACTOR = 3.0        # speech = this much louder than the room noise...
VAD_MIN_RMS = 300.0           # ...but never below this floor...
VAD_MAX_RMS = 2500.0          # ...or above this ceiling (if someone talks during calibration)
VAD_MIN_SPEECH_MS = 150       # voiced run needed to count as speech (ignores clicks)
VAD_PREROLL_MS = 300          # audio kept from before speech started

# USB audio card is resolved lazily at first use (card number can shift on reboot)
_audio_card: str | None = None


def _find_usb_audio_card() -> str:
    """Scan ALSA capture devices and return the plughw string for the first
    USB Audio Device found (excludes HDMI and the C920 webcam's audio).
    Raises RuntimeError with a diagnostic message if nothing is found.
    """
    result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
    # Example line: card 2: Device [USB Audio Device], device 0: USB Audio [USB Audio]
    for line in result.stdout.splitlines():
        if "USB Audio Device" in line:
            m = re.match(r"card\s+\d+:\s+(\S+)\s+\[", line)
            if m:
                return f"plughw:CARD={m.group(1)},DEV=0"
    raise RuntimeError(
        "No USB audio capture device found — is the Yahboom mic plugged in?\n"
        f"Devices seen by arecord -l:\n{result.stdout or '(none)'}"
    )


def _get_audio_card() -> str:
    """Return the resolved USB audio card string, detecting it on first call."""
    global _audio_card
    if _audio_card is None:
        _audio_card = _find_usb_audio_card()
    return _audio_card


def _forget_audio_card() -> None:
    """Drop the cached card so the next turn re-detects it (the card name/number
    can change if the USB audio device drops out and re-enumerates)."""
    global _audio_card
    _audio_card = None


def _unlink_quiet(*paths: str | None) -> None:
    """Remove temp files, ignoring ones that are already gone."""
    for path in paths:
        if path:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

VISION_TRIGGERS = [
    "what do you see", "look at", "describe what", "show me", "camera",
    "what is this", "take a picture", "take a photo",
]


# ── Runtime state shared between the loop thread and the GUI ──────────────────

class _StopEvent(threading.Event):
    """``stop`` that also trips ``interrupt``, so every wait that watches
    ``interrupt`` (mode switches) wakes on stop too."""

    def __init__(self, interrupt: threading.Event) -> None:
        super().__init__()
        self._interrupt = interrupt

    def set(self) -> None:
        super().set()
        self._interrupt.set()


@dataclass
class RuntimeState:
    """Mutable runtime config. Protect mutations with self.lock.

    ``scenario_id`` None = plain voice assistant, else the overlay scenario
    driving the console. ``interrupt`` is set when the loop should drop what
    it's waiting on (stop, or the mode changed); waits use it, not ``stop``.
    """
    text_model: str
    vision_model: str
    voice: Voice
    volume_gain: float
    personality: Personality
    vad_threshold: float = 0.0          # speech threshold (int16 RMS); 0 = auto
    vad_silence_ms: int = 800           # pause that ends an utterance
    scenario_id: str | None = None      # None = plain voice assistant
    lock: threading.Lock = field(default_factory=threading.Lock)
    interrupt: threading.Event = field(default_factory=threading.Event)
    stop: threading.Event = field(init=False)

    def __post_init__(self) -> None:
        self.stop = _StopEvent(self.interrupt)

    def snapshot(self) -> tuple[str, str, Voice, float, Personality]:
        """Read-consistent snapshot of the live values."""
        with self.lock:
            return self.text_model, self.vision_model, self.voice, self.volume_gain, self.personality

    def set_voice(self, voice: Voice) -> None:
        with self.lock:
            self.voice = voice

    def set_volume(self, gain: float) -> None:
        with self.lock:
            self.volume_gain = gain

    def set_personality(self, personality: Personality) -> None:
        with self.lock:
            self.personality = personality

    def vad_settings(self) -> tuple[float, int]:
        """(speech threshold, 0 = auto; end-of-utterance pause in ms)."""
        with self.lock:
            return self.vad_threshold, self.vad_silence_ms

    def set_vad_threshold(self, threshold: float) -> None:
        with self.lock:
            self.vad_threshold = threshold

    def set_vad_silence_ms(self, silence_ms: int) -> None:
        with self.lock:
            self.vad_silence_ms = silence_ms

    def current_scenario(self) -> str | None:
        with self.lock:
            return self.scenario_id

    def set_scenario(self, scenario_id: str | None) -> None:
        """Switch modes: the running loop notices via ``interrupt`` and restarts."""
        with self.lock:
            changed = scenario_id != self.scenario_id
            self.scenario_id = scenario_id
        if changed:
            self.interrupt.set()


def make_default_state() -> RuntimeState:
    """Build a RuntimeState seeded from the on-disk config."""
    preset = load_preset()
    return RuntimeState(
        text_model=preset.text_model,
        vision_model=preset.vision_model,
        voice=load_voice(),
        volume_gain=load_volume_gain(),
        personality=load_personality(),
        vad_threshold=load_vad_threshold(),
        vad_silence_ms=load_vad_silence_ms(),
        scenario_id=load_scenario(),
    )


# ── Status reporting (loop thread -> GUI) ─────────────────────────────────────

# Status events sent to the GUI via a Queue. Each item is a (kind, text) tuple.
#   kind == "status" — short status badge ("Listening", "Thinking", etc.)
#   kind == "user"   — what the user said
#   kind == "asst"   — what the assistant replied
#   kind == "error"  — error message
#   kind == "level"  — "<mic rms> <speech threshold>" while listening (GUI only)
StatusEvent = tuple[str, str]


def _emit(queue: Queue | None, kind: str, text: str) -> None:
    """Push a status event to the GUI queue if one is attached, else print."""
    if queue is not None:
        queue.put((kind, text))
    else:
        # Headless mode: just print
        prefix = {"status": "", "user": "   You said: ", "asst": "   Assistant: ", "error": "   Error: "}.get(kind, "")
        print(f"{prefix}{text}")


# ── Audio I/O ─────────────────────────────────────────────────────────────────

def record_utterance(duration_secs: int = 5) -> str:
    """Record from microphone to a temp WAV file (16kHz mono PCM, ready for Whisper)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    tmp16 = tmp.name.replace(".wav", "_16k.wav")
    try:
        subprocess.run([
            "arecord", "-D", _get_audio_card(),
            "-f", "cd", "-t", "wav", "-d", str(duration_secs), tmp.name
        ], check=True, capture_output=True)
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp.name,
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", tmp16
        ], check=True, capture_output=True)
    except BaseException:
        _unlink_quiet(tmp16)
        raise
    finally:
        _unlink_quiet(tmp.name)
    return tmp16


def _frame_rms(frame: bytes) -> float:
    import numpy as np   # ships with opencv in the venv
    samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0


def _vad_segment(frames: Iterable[bytes], *, listen_secs: float = LISTEN_WINDOW_SECS,
                 max_secs: float = MAX_UTTERANCE_SECS,
                 silence_ms: int = 800,
                 fixed_threshold: float = 0.0,
                 on_level: Callable[[float, float], None] | None = None) -> bytes | None:
    """Energy-based end-of-speech detection over 16-bit mono PCM frames.

    Calibrates a speech threshold from the first VAD_CALIBRATE_MS of room
    noise, waits up to ``listen_secs`` for speech, then returns the utterance
    (plus a short pre-roll so the first syllable isn't clipped) once
    ``silence_ms`` of quiet follows it, or ``max_secs`` elapse. Returns None
    if nobody spoke. Pure function of the frames so it can be tested offline.

    ``fixed_threshold`` > 0 skips calibration. ``on_level(rms, threshold)``
    is called for every frame (drives the control panel's mic meter).
    """
    calib_frames = VAD_CALIBRATE_MS // VAD_FRAME_MS
    preroll: deque[bytes] = deque(maxlen=VAD_PREROLL_MS // VAD_FRAME_MS)
    noise: list[float] = []
    threshold = fixed_threshold or VAD_MIN_RMS
    voiced_run = 0
    speech: list[bytes] | None = None
    started_at = 0
    silence_run = 0

    for n, frame in enumerate(frames, start=1):
        rms = _frame_rms(frame)
        if on_level is not None:
            on_level(rms, threshold)
        if speech is None:
            preroll.append(frame)
            if not fixed_threshold and n <= calib_frames:
                noise.append(rms)
                if n == calib_frames:
                    threshold = min(VAD_MAX_RMS, max(VAD_MIN_RMS, VAD_NOISE_FACTOR * sum(noise) / len(noise)))
                continue
            voiced_run = voiced_run + 1 if rms >= threshold else 0
            if voiced_run * VAD_FRAME_MS >= VAD_MIN_SPEECH_MS:
                speech = list(preroll)
                started_at = n
            elif n * VAD_FRAME_MS >= listen_secs * 1000:
                return None
        else:
            speech.append(frame)
            silence_run = silence_run + 1 if rms < threshold else 0
            if silence_run * VAD_FRAME_MS >= silence_ms:
                break
            if (n - started_at) * VAD_FRAME_MS >= max_secs * 1000:
                break
    return b"".join(speech) if speech else None


def record_until_silence(stop: threading.Event | None = None, *,
                         threshold: float = 0.0, silence_ms: int = 800,
                         on_level: Callable[[float, float], None] | None = None) -> str | None:
    """Record until the speaker stops talking; return a 16 kHz mono WAV path.

    Returns None if nobody started speaking within LISTEN_WINDOW_SECS (or
    ``stop`` was set), so the caller can simply listen again. ``threshold``
    0 means calibrate to the room; see _vad_segment for ``on_level``.
    """
    proc = subprocess.Popen(
        ["arecord", "-D", _get_audio_card(), "-q",
         "-f", "S16_LE", "-r", str(VAD_RATE), "-c", "1", "-t", "raw"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )

    def _frames():
        while stop is None or not stop.is_set():
            chunk = proc.stdout.read(VAD_FRAME_BYTES)
            if len(chunk) < VAD_FRAME_BYTES:   # EOF: arecord died (device gone?)
                proc.wait(timeout=2.0)
                raise RuntimeError(f"arecord stopped unexpectedly (exit {proc.returncode})")
            yield chunk

    try:
        pcm = _vad_segment(_frames(), fixed_threshold=threshold,
                           silence_ms=silence_ms, on_level=on_level)
    finally:
        _stop_arecord(proc)
        proc.stdout.close()
    if pcm is None:
        return None

    tmp = tempfile.NamedTemporaryFile(suffix="_16k.wav", delete=False)
    tmp.close()
    with wave.open(tmp.name, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(VAD_RATE)
        w.writeframes(pcm)
    return tmp.name


def capture_image() -> str:
    """Capture a frame from the USB camera."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Camera capture failed")
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    cv2.imwrite(tmp.name, frame)
    return tmp.name


def transcribe(wav_path: str) -> str:
    """Transcribe audio using whisper.cpp."""
    result = subprocess.run(
        [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", wav_path, "--no-timestamps"],
        capture_output=True, text=True, timeout=30
    )
    lines = [
        l.strip() for l in result.stdout.splitlines()
        if l.strip() and not l.startswith("whisper_")
    ]
    return " ".join(lines)


def stream_llm(prompt: str, text_model: str, vision_model: str,
               system_prompt: str = "", image_path: str | None = None) -> Iterator[str]:
    """Send prompt to Ollama via /api/chat and yield the reply as it's generated.

    The request (including reading ``image_path``) happens before this
    returns, so the caller may delete the image straight away.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if image_path:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        messages.append({"role": "user", "content": prompt, "images": [img_b64]})
        model = vision_model
    else:
        messages.append({"role": "user", "content": prompt})
        model = text_model

    data = json.dumps({"model": model, "messages": messages, "stream": True,
                       "keep_alive": KEEP_ALIVE}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/chat", data=data, headers={"Content-Type": "application/json"}
    )
    # Vision cold-start can take 5+ minutes on CPU-only Pi 5; text is much faster.
    timeout = 600 if image_path else 300
    return _iter_chat_stream(urllib.request.urlopen(req, timeout=timeout))


def _iter_chat_stream(resp) -> Iterator[str]:
    """Yield message deltas from Ollama's newline-delimited JSON stream."""
    with resp:
        for line in resp:
            if not line.strip():
                continue
            chunk = json.loads(line)
            if "error" in chunk:
                raise RuntimeError(f"Ollama: {chunk['error']}")
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                yield piece
            if chunk.get("done"):
                return


def ask_llm(prompt: str, text_model: str, vision_model: str,
            system_prompt: str = "", image_path: str | None = None) -> str:
    """Whole-reply convenience wrapper around stream_llm()."""
    return "".join(stream_llm(prompt, text_model, vision_model, system_prompt, image_path))


def warm_up(model: str) -> None:
    """Load ``model`` into Ollama's memory ahead of the first question.

    An empty /api/generate request just loads the model; keep_alive then
    holds it resident between turns.
    """
    data = json.dumps({"model": model, "keep_alive": KEEP_ALIVE}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/generate", data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        resp.read()


def _warm_up_in_background(model: str, status_q: Queue | None) -> None:
    def _run() -> None:
        try:
            warm_up(model)
        except Exception as e:
            _emit(status_q, "error", f"Could not preload {model}: {e}")
    threading.Thread(target=_run, daemon=True, name="ollama-warmup").start()


# Split after sentence punctuation followed by whitespace, or at line breaks.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def _sentences(pieces: Iterable[str], min_chars: int = 20) -> Iterator[str]:
    """Regroup streamed text into sentences for TTS.

    ``min_chars`` keeps very short fragments ("Hi.", "Dr.") glued to the
    next sentence so Piper isn't started for a syllable at a time.
    """
    buf = ""
    for piece in pieces:
        buf += piece
        while (m := _SENTENCE_END.search(buf, min_chars)) is not None:
            sentence, buf = buf[:m.start()].strip(), buf[m.end():]
            if sentence:
                yield sentence
    if buf.strip():
        yield buf.strip()


def _speak_streamed(sentences: Iterable[str], state: RuntimeState,
                    status_q: Queue | None) -> str:
    """Speak sentences as they arrive while the LLM keeps generating.

    A worker thread synthesizes/plays each sentence in order, so the first
    one is heard as soon as it's complete instead of after the whole reply.
    Returns the full text. Re-reads voice/gain per sentence so a GUI change
    mid-reply is honored.
    """
    q: Queue[str | None] = Queue()
    errors: list[BaseException] = []

    def _worker() -> None:
        first = True
        while (sentence := q.get()) is not None:
            if errors:
                continue            # playback failed — drain without speaking
            if first:
                _emit(status_q, "status", "Speaking")
                first = False
            _, _, voice, gain, _ = state.snapshot()
            try:
                speak(sentence, voice, gain)
            except BaseException as e:
                errors.append(e)

    worker = threading.Thread(target=_worker, daemon=True, name="tts")
    worker.start()
    parts: list[str] = []
    try:
        for sentence in sentences:
            parts.append(sentence)
            q.put(sentence)
    finally:
        q.put(None)
        worker.join()
    if errors:
        raise errors[0]
    return " ".join(parts)


def speak(text: str, voice: Voice, volume_gain: float) -> None:
    """Synthesize text via Piper, apply software volume gain via ffmpeg, play it."""
    raw = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    raw_path = raw.name
    raw.close()
    amplified_path = None

    try:
        # 1) Piper synthesizes raw WAV using the supplied voice
        subprocess.run(
            [PIPER_BIN, "--model", voice_model_path(voice), "--output_file", raw_path],
            input=text, text=True, check=True, capture_output=True,
        )

        # 2) ffmpeg applies software volume gain (1.0 = unity, 2.0 = +6dB).
        #    Skip the re-encode if gain is ~1.0 to avoid latency on the no-op case.
        if abs(volume_gain - 1.0) < 0.01:
            play_path = raw_path
        else:
            amplified_path = raw_path.replace(".wav", "_amp.wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", raw_path,
                 "-filter:a", f"volume={volume_gain}",
                 "-c:a", "pcm_s16le", amplified_path],
                check=True, capture_output=True,
            )
            play_path = amplified_path

        # 3) Play through the Yahboom USB speaker (same card as mic)
        subprocess.run(["aplay", "-D", _get_audio_card(), play_path], check=True, capture_output=True)
    finally:
        _unlink_quiet(raw_path, amplified_path)


# ── One conversation turn ─────────────────────────────────────────────────────

def run_voice_turn(state: RuntimeState, status_q: Queue | None = None) -> None:
    """One conversation turn — reads live state for every step."""
    if VAD_ENABLED:
        _emit(status_q, "status", "Listening")
        threshold, silence_ms = state.vad_settings()
        wav = record_until_silence(state.interrupt, threshold=threshold, silence_ms=silence_ms,
                                   on_level=_level_reporter(status_q))
        if wav is None:
            return          # nobody spoke — the loop just listens again
    else:
        _emit(status_q, "status", "Listening (10s)")
        wav = record_utterance(10)

    _emit(status_q, "status", "Transcribing")
    try:
        user_text = transcribe(wav)
    finally:
        _unlink_quiet(wav)

    text_model, vision_model, voice, gain, personality = state.snapshot()

    _emit(status_q, "user", user_text)
    if not user_text.strip():
        _emit(status_q, "status", "No speech detected")
        speak("I did not catch that. Please try again.", voice, gain)
        return

    image_path = None
    if any(trigger in user_text.lower() for trigger in VISION_TRIGGERS):
        _emit(status_q, "status", "Capturing image")
        image_path = capture_image()

    _emit(status_q, "status", "Thinking")
    try:
        pieces = stream_llm(
            user_text, text_model, vision_model,
            system_prompt=personality.system_prompt,
            image_path=image_path,
        )
    finally:
        _unlink_quiet(image_path)

    # Speak each sentence as soon as it's generated rather than waiting for
    # the whole reply; voice/gain are re-read per sentence.
    response = _speak_streamed(_sentences(pieces), state, status_q)
    _emit(status_q, "asst", response)
    _emit(status_q, "status", "Pausing")
    state.interrupt.wait(3.0)   # 3s grace period before listening again
    _emit(status_q, "status", "Idle")


def _level_reporter(status_q: Queue | None) -> Callable[[float, float], None] | None:
    """Feed the GUI's mic meter ~10x/s. Headless mode gets nothing (it would
    print a line per frame)."""
    if status_q is None:
        return None
    frames = 0

    def report(rms: float, threshold: float) -> None:
        nonlocal frames
        frames += 1
        if frames % 3 == 0:     # 30 ms frames -> every ~90 ms
            status_q.put(("level", f"{rms:.0f} {threshold:.0f}"))
    return report


# ── Overlay turn (PTT-gated, scenario-driven, tool-use LLM) ───────────────────

def _record_ptt_gated(hal, status_q: Queue | None, max_secs: int,
                      stop: threading.Event | None = None) -> str | None:
    """Block until PTT press, then record while held; return wav path or None.

    True start-on-press / stop-on-release: starts ``arecord`` with no
    ``-d`` (record indefinitely), then terminates the subprocess on PTT
    release. ``max_secs`` is a *safety cap* that fires only if PTT is
    still held past the cap — it protects against a stuck button rather
    than dictating recording length.

    Uses the HAL state mirror's PTT field plus the event queue for edges.
    Returns the path to a 16 kHz mono WAV ready for Whisper, or None if
    ``stop`` is set while waiting. Raises ConnectionError if the HAL link
    drops while waiting, so the caller can reconnect.
    """
    import time as _time

    # Drain any stale ptt event so we react only to a fresh press
    _emit(status_q, "status", "Waiting for PTT")
    while True:
        if stop is not None and stop.is_set():
            return None
        if not hal.state().get("connected", True):
            raise ConnectionError("overlay HAL disconnected")
        msg = hal.wait_for_event("ptt", timeout=0.5)
        if msg is None:
            continue
        if int(msg.get("state", 0)) == 1:
            break

    _emit(status_q, "status", "Recording")
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    # Open-ended recording: NO -d. We terminate on PTT release.
    proc = _start_arecord(_get_audio_card(), tmp.name)
    t0 = _time.monotonic()
    stop_reason = "release"
    try:
        while True:
            # State-mirror check is the cheap path
            if hal.state().get("ptt") == 0:
                break
            # Block briefly on the event queue so a race-y release is
            # caught even if the state mirror update hasn't landed yet
            msg = hal.wait_for_event("ptt", timeout=0.1)
            if msg is not None and int(msg.get("state", 1)) == 0:
                break
            if _time.monotonic() - t0 > max_secs:
                stop_reason = "safety_cap"
                break
            # arecord died on its own (e.g. audio device unplugged)?
            if proc.poll() is not None:
                stop_reason = f"arecord_exited({proc.returncode})"
                break
    finally:
        _stop_arecord(proc)

    elapsed = _time.monotonic() - t0
    _emit(status_q, "status",
          f"Recorded {elapsed:.1f}s ({stop_reason})")

    # Resample to 16 kHz mono for Whisper, same as record_utterance
    tmp16 = tmp.name.replace(".wav", "_16k.wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp.name,
             "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", tmp16],
            check=True, capture_output=True,
        )
    except BaseException:
        _unlink_quiet(tmp16)
        raise
    finally:
        _unlink_quiet(tmp.name)
    return tmp16


def _start_arecord(card: str, out_path: str) -> subprocess.Popen:
    """Start arecord with no fixed duration — runs until terminated.

    Factored out of ``_record_ptt_gated`` so tests can mock just this
    function and still exercise the start-on-press / stop-on-release
    state machine.
    """
    return subprocess.Popen(
        ["arecord", "-D", card, "-f", "cd", "-t", "wav", out_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _stop_arecord(proc: subprocess.Popen) -> None:
    """Terminate an arecord subprocess cleanly; fall back to kill."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass


def run_overlay_turn(state: RuntimeState, runtime, history: list,
                     status_q: Queue | None = None) -> list:
    """One PTT-gated turn through the scenario tool-use loop.

    ``runtime`` is an ``overlay.scenario.ScenarioRuntime`` already bound to a
    connected HAL client. ``history`` is rolling conversation state — the
    system prompt is rebuilt every turn so it reflects live HAL state.
    """
    from overlay.scenario.llm import run_turn   # local import: keep top-level light

    hal = runtime.hal
    wav = _record_ptt_gated(hal, status_q, OVERLAY_PTT_MAX_SECS, stop=state.interrupt)
    if wav is None:
        return history

    _emit(status_q, "status", "Transcribing")
    try:
        user_text = transcribe(wav)
    finally:
        _unlink_quiet(wav)

    _, _, voice, gain, _ = state.snapshot()
    _emit(status_q, "user", user_text)
    if not user_text.strip():
        _emit(status_q, "status", "No speech detected")
        speak("I did not catch that. Try again.", voice, gain)
        return history

    _emit(status_q, "status", "Thinking")

    def _observer(name, args, result):
        _emit(status_q, "status", f"tool {name}")

    speech, history = run_turn(
        runtime, user_text,
        model=OVERLAY_MODEL,
        history=history,
        on_tool_call=_observer,
    )

    _emit(status_q, "asst", speech)
    if speech:
        _, _, voice, gain, _ = state.snapshot()
        _emit(status_q, "status", "Speaking")
        speak(speech, voice, gain)
    _emit(status_q, "status", "Idle")
    return history


def _run_overlay_loop(state: RuntimeState, status_q: Queue | None, scenario_id: str) -> None:
    """Overlay-mode loop. Sets up the HAL + scenario, then PTT-driven turns
    until ``state.interrupt`` (stop or a mode switch)."""
    # Late imports so the existing voice loop has no hard dependency on the
    # overlay package — if overlay/ is missing or its deps aren't installed,
    # the non-overlay path still works.
    from overlay.pi5_hal.client import HalClient
    from overlay.pi5_hal.transport import open_transport
    from overlay.scenario.runtime import ScenarioRuntime
    from overlay.scenario.demo import SCENARIOS

    if scenario_id not in SCENARIOS:
        _emit(status_q, "error",
              f"Unknown overlay scenario {scenario_id!r}; "
              f"options: {sorted(SCENARIOS)}")
        return

    scenario = SCENARIOS[scenario_id]
    try:
        transport = open_transport(OVERLAY_HAL_URL)
    except ValueError as e:
        _emit(status_q, "error", str(e))
        return
    hal = HalClient(transport)
    runtime = ScenarioRuntime(hal, scenario)

    history: list = []
    backoff = 2.0
    try:
        while not state.interrupt.is_set():
            # (Re)connect whenever the link is down — at startup, or after the
            # simulator / RP2040 drops. The panel may simply not be up yet.
            if not hal.state()["connected"]:
                _emit(status_q, "status", f"Connecting overlay HAL @ {OVERLAY_HAL_URL}")
                try:
                    hal.disconnect()   # reap the previous rx thread / socket
                    hal.connect()
                except Exception as e:
                    _emit(status_q, "error",
                          f"Overlay HAL unreachable at {OVERLAY_HAL_URL} ({e}); "
                          f"retrying in {backoff:.0f}s")
                    if state.interrupt.wait(backoff):
                        break
                    backoff = min(backoff * 2, 30.0)
                    continue
                backoff = 2.0
                _emit(status_q, "status", f"Overlay: {scenario.name}")
            try:
                history = run_overlay_turn(state, runtime, history, status_q)
            except KeyboardInterrupt:
                _emit(status_q, "status", "Stopped")
                state.stop.set()
                break
            except ConnectionError as e:
                _emit(status_q, "error", f"{e} — reconnecting")
                if state.interrupt.wait(1.0):
                    break
            except Exception as e:
                _emit(status_q, "error", f"{e}\n\n{traceback.format_exc()}")
                _forget_audio_card()
                if state.interrupt.wait(2.0):
                    break
    finally:
        try:
            hal.disconnect()
        except Exception:
            pass


# ── Loop runner (used by both CLI and the Tk panel) ───────────────────────────

def _run_voice_loop(state: RuntimeState, status_q: Queue | None) -> None:
    """Plain voice-assistant turns until ``state.interrupt``."""
    while not state.interrupt.is_set():
        try:
            run_voice_turn(state, status_q)
        except KeyboardInterrupt:
            _emit(status_q, "status", "Stopped")
            state.stop.set()
            break
        except Exception as e:
            _emit(status_q, "error", f"{e}\n\n{traceback.format_exc()}")
            _forget_audio_card()   # re-detect in case the USB audio device re-enumerated
            # Brief pause to avoid a tight failure loop
            if state.interrupt.wait(2.0):
                break


def run_loop(state: RuntimeState, status_q: Queue | None = None) -> None:
    """Run the current mode until ``state.stop``; switch when the mode changes.

    The mode is ``state.scenario_id`` (None = plain voice assistant). Picking
    another one in the control panel sets ``state.interrupt``: the running
    mode finishes its current turn, then the new one starts.
    """
    while not state.stop.is_set():
        state.interrupt.clear()
        scenario_id = state.current_scenario()
        # Load the mode's model while the first utterance is being recorded,
        # so the first answer doesn't also pay the model's cold-load time.
        _warm_up_in_background(OVERLAY_MODEL if scenario_id else state.text_model, status_q)
        if scenario_id:
            _emit(status_q, "status", f"Scenario mode ({scenario_id})")
            _run_overlay_loop(state, status_q, scenario_id)
        else:
            _run_voice_loop(state, status_q)
        if not state.interrupt.is_set():
            # The mode gave up (e.g. unknown scenario, bad HAL endpoint) —
            # wait for another pick instead of retrying in a tight loop.
            _emit(status_q, "status", "Stopped — pick another mode")
            state.interrupt.wait()


# ── Headless CLI entrypoint ───────────────────────────────────────────────────

if __name__ == "__main__":
    state = make_default_state()
    print("=" * 50)
    print("  Mini-AI Voice Pipeline (headless)")
    print(f"  Text:   {state.text_model}")
    print(f"  Vision: {state.vision_model}")
    print(f"  Voice:  {state.voice.label}")
    print(f"  Volume gain: {state.volume_gain}x")
    print(f"  Mode:   {state.scenario_id or 'voice assistant'}")
    print("  Speak naturally. Say 'what do you see' for vision.")
    print("  Press Ctrl+C to quit.")
    print("  (For live controls, run mini_ai_panel.py instead.)")
    print("=" * 50)
    try:
        run_loop(state)
    except KeyboardInterrupt:
        print("Goodbye!")
