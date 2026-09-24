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
from dataclasses import dataclass, field
from queue import Queue, Empty

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
# Env knobs:
#   MINI_AI_OVERLAY=true|false      enable the overlay path (default false)
#   MINI_AI_OVERLAY_SCENARIO=<id>   scenario id; default space_command_launch
#   MINI_AI_OVERLAY_HAL=<url>       HAL endpoint; default ws://127.0.0.1:8765/hal
#   MINI_AI_OVERLAY_MODEL=<name>    Ollama model; default qwen2.5:14b
OVERLAY_ENABLED = os.environ.get("MINI_AI_OVERLAY", "").lower() in ("1", "true", "yes")
OVERLAY_SCENARIO_ID = os.environ.get("MINI_AI_OVERLAY_SCENARIO", "space_command_launch")
OVERLAY_HAL_URL = os.environ.get("MINI_AI_OVERLAY_HAL", "ws://127.0.0.1:8765/hal")
OVERLAY_MODEL = os.environ.get("MINI_AI_OVERLAY_MODEL", "qwen2.5:14b")
OVERLAY_PTT_MAX_SECS = int(os.environ.get("MINI_AI_OVERLAY_PTT_MAX", "30"))

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

@dataclass
class RuntimeState:
    """Mutable runtime config. Protect mutations with self.lock."""
    text_model: str
    vision_model: str
    voice: Voice
    volume_gain: float
    personality: Personality
    lock: threading.Lock = field(default_factory=threading.Lock)
    stop: threading.Event = field(default_factory=threading.Event)

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


def make_default_state() -> RuntimeState:
    """Build a RuntimeState seeded from the on-disk config."""
    preset = load_preset()
    return RuntimeState(
        text_model=preset.text_model,
        vision_model=preset.vision_model,
        voice=load_voice(),
        volume_gain=load_volume_gain(),
        personality=load_personality(),
    )


# ── Status reporting (loop thread -> GUI) ─────────────────────────────────────

# Status events sent to the GUI via a Queue. Each item is a (kind, text) tuple.
#   kind == "status" — short status badge ("Listening", "Thinking", etc.)
#   kind == "user"   — what the user said
#   kind == "asst"   — what the assistant replied
#   kind == "error"  — error message
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


def ask_llm(prompt: str, text_model: str, vision_model: str,
            system_prompt: str = "", image_path: str = None) -> str:
    """Send prompt to Ollama via /api/chat, injecting the system prompt if set."""
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

    data = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/chat", data=data, headers={"Content-Type": "application/json"}
    )
    # Vision cold-start can take 5+ minutes on CPU-only Pi 5; text is much faster.
    timeout = 600 if image_path else 300
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())["message"]["content"]


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
        response = ask_llm(
            user_text, text_model, vision_model,
            system_prompt=personality.system_prompt,
            image_path=image_path,
        )
    finally:
        if image_path:
            os.unlink(image_path)

    _emit(status_q, "asst", response)

    # Re-snapshot voice/gain so a mid-turn GUI change is honored
    _, _, voice, gain, _ = state.snapshot()
    _emit(status_q, "status", "Speaking")
    speak(response, voice, gain)
    _emit(status_q, "status", "Pausing")
    state.stop.wait(3.0)   # 3s grace period before listening again
    _emit(status_q, "status", "Idle")


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
    wav = _record_ptt_gated(hal, status_q, OVERLAY_PTT_MAX_SECS, stop=state.stop)
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


def _run_overlay_loop(state: RuntimeState, status_q: Queue | None) -> None:
    """Overlay-mode loop. Sets up the HAL + scenario, then PTT-driven turns."""
    # Late imports so the existing voice loop has no hard dependency on the
    # overlay package — if overlay/ is missing or its deps aren't installed,
    # the non-overlay path still works.
    from overlay.pi5_hal.client import HalClient
    from overlay.pi5_hal.transport import WebsocketTransport
    from overlay.scenario.runtime import ScenarioRuntime
    from overlay.scenario.demo import SCENARIOS

    if OVERLAY_SCENARIO_ID not in SCENARIOS:
        _emit(status_q, "error",
              f"Unknown overlay scenario {OVERLAY_SCENARIO_ID!r}; "
              f"options: {sorted(SCENARIOS)}")
        return

    scenario = SCENARIOS[OVERLAY_SCENARIO_ID]
    hal = HalClient(WebsocketTransport(OVERLAY_HAL_URL))
    runtime = ScenarioRuntime(hal, scenario)

    history: list = []
    backoff = 2.0
    try:
        while not state.stop.is_set():
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
                    if state.stop.wait(backoff):
                        break
                    backoff = min(backoff * 2, 30.0)
                    continue
                backoff = 2.0
                _emit(status_q, "status", f"Overlay: {scenario.name}")
            try:
                history = run_overlay_turn(state, runtime, history, status_q)
            except KeyboardInterrupt:
                _emit(status_q, "status", "Stopped")
                break
            except ConnectionError as e:
                _emit(status_q, "error", f"{e} — reconnecting")
                if state.stop.wait(1.0):
                    break
            except Exception as e:
                _emit(status_q, "error", f"{e}\n\n{traceback.format_exc()}")
                _forget_audio_card()
                if state.stop.wait(2.0):
                    break
    finally:
        try:
            hal.disconnect()
        except Exception:
            pass


# ── Loop runner (used by both CLI and the Tk panel) ───────────────────────────

def run_loop(state: RuntimeState, status_q: Queue | None = None) -> None:
    """Run conversation turns until state.stop is set or KeyboardInterrupt."""
    if OVERLAY_ENABLED:
        _emit(status_q, "status",
              f"Overlay mode ({OVERLAY_SCENARIO_ID}) — set MINI_AI_OVERLAY= to disable")
        _run_overlay_loop(state, status_q)
        return
    while not state.stop.is_set():
        try:
            run_voice_turn(state, status_q)
        except KeyboardInterrupt:
            _emit(status_q, "status", "Stopped")
            break
        except Exception as e:
            _emit(status_q, "error", f"{e}\n\n{traceback.format_exc()}")
            _forget_audio_card()   # re-detect in case the USB audio device re-enumerated
            # Brief pause to avoid a tight failure loop
            if state.stop.wait(2.0):
                break


# ── Headless CLI entrypoint ───────────────────────────────────────────────────

if __name__ == "__main__":
    state = make_default_state()
    print("=" * 50)
    print("  Mini-AI Voice Pipeline (headless)")
    print(f"  Text:   {state.text_model}")
    print(f"  Vision: {state.vision_model}")
    print(f"  Voice:  {state.voice.label}")
    print(f"  Volume gain: {state.volume_gain}x")
    print("  Speak naturally. Say 'what do you see' for vision.")
    print("  Press Ctrl+C to quit.")
    print("  (For live controls, run mini_ai_panel.py instead.)")
    print("=" * 50)
    try:
        run_loop(state)
    except KeyboardInterrupt:
        print("Goodbye!")
