#!/home/miniai_admin/mini-ai/.venv/bin/python3
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
import base64
import json
import threading
import urllib.request
from dataclasses import dataclass, field
from queue import Queue, Empty

import cv2

# Make sibling modules importable when launched from anywhere
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mini_ai_config import (
    Voice,
    load_preset,
    load_voice,
    load_volume_gain,
    voice_model_path,
)

HOME = os.path.expanduser("~")
WHISPER_BIN = os.path.join(HOME, "whisper.cpp/build/bin/whisper-cli")
WHISPER_MODEL = os.path.join(HOME, "whisper.cpp/models/ggml-base.en.bin")
PIPER_BIN = os.path.join(HOME, "mini-ai/.venv/bin/piper")
OLLAMA_URL = "http://localhost:11434/api"
AUDIO_CARD = "default"
CAMERA_INDEX = 0

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
    lock: threading.Lock = field(default_factory=threading.Lock)
    stop: threading.Event = field(default_factory=threading.Event)

    def snapshot(self) -> tuple[str, str, Voice, float]:
        """Read-consistent snapshot of the live values."""
        with self.lock:
            return self.text_model, self.vision_model, self.voice, self.volume_gain

    def set_voice(self, voice: Voice) -> None:
        with self.lock:
            self.voice = voice

    def set_volume(self, gain: float) -> None:
        with self.lock:
            self.volume_gain = gain


def make_default_state() -> RuntimeState:
    """Build a RuntimeState seeded from the on-disk config."""
    preset = load_preset()
    return RuntimeState(
        text_model=preset.text_model,
        vision_model=preset.vision_model,
        voice=load_voice(),
        volume_gain=load_volume_gain(),
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
    subprocess.run([
        "arecord", "-D", AUDIO_CARD,
        "-f", "cd", "-t", "wav", "-d", str(duration_secs), tmp.name
    ], check=True, capture_output=True)
    tmp16 = tmp.name.replace(".wav", "_16k.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", tmp.name,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", tmp16
    ], check=True, capture_output=True)
    os.unlink(tmp.name)
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


def ask_llm(prompt: str, text_model: str, vision_model: str, image_path: str = None) -> str:
    """Send prompt to Ollama using the supplied model tags."""
    if image_path:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        data = json.dumps({
            "model": vision_model,
            "messages": [{"role": "user", "content": prompt, "images": [img_b64]}],
            "stream": False,
        }).encode()
        url = f"{OLLAMA_URL}/chat"
    else:
        data = json.dumps({
            "model": text_model,
            "prompt": prompt,
            "stream": False,
        }).encode()
        url = f"{OLLAMA_URL}/generate"
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    # Vision cold-start can take 5+ minutes on CPU-only Pi 5; text is much faster.
    timeout = 600 if image_path else 300
    resp = urllib.request.urlopen(req, timeout=timeout)
    result = json.loads(resp.read())
    if image_path:
        return result["message"]["content"]
    return result["response"]


def speak(text: str, voice: Voice, volume_gain: float) -> None:
    """Synthesize text via Piper, apply software volume gain via ffmpeg, play it."""
    raw = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    raw_path = raw.name
    raw.close()

    # 1) Piper synthesizes raw WAV using the supplied voice
    subprocess.run(
        [PIPER_BIN, "--model", voice_model_path(voice), "--output_file", raw_path],
        input=text, text=True, check=True, capture_output=True,
    )

    # 2) ffmpeg applies software volume gain (1.0 = unity, 2.0 = +6dB).
    #    Skip the re-encode if gain is ~1.0 to avoid latency on the no-op case.
    if abs(volume_gain - 1.0) < 0.01:
        play_path = raw_path
        amplified_path = None
    else:
        amplified_path = raw_path.replace(".wav", "_amp.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path,
             "-filter:a", f"volume={volume_gain}",
             "-c:a", "pcm_s16le", amplified_path],
            check=True, capture_output=True,
        )
        play_path = amplified_path

    # 3) Play through default ALSA device (configured in ~/.asoundrc)
    subprocess.run(["aplay", play_path], check=True, capture_output=True)

    os.unlink(raw_path)
    if amplified_path and amplified_path != raw_path:
        try:
            os.unlink(amplified_path)
        except FileNotFoundError:
            pass


# ── One conversation turn ─────────────────────────────────────────────────────

def run_voice_turn(state: RuntimeState, status_q: Queue | None = None) -> None:
    """One conversation turn — reads live state for every step."""
    _emit(status_q, "status", "Listening (5s)")
    wav = record_utterance(5)

    _emit(status_q, "status", "Transcribing")
    user_text = transcribe(wav)
    os.unlink(wav)

    text_model, vision_model, voice, gain = state.snapshot()

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
        response = ask_llm(user_text, text_model, vision_model, image_path=image_path)
    finally:
        if image_path:
            os.unlink(image_path)

    _emit(status_q, "asst", response)

    # Re-snapshot voice/gain so a mid-turn GUI change is honored
    _, _, voice, gain = state.snapshot()
    _emit(status_q, "status", "Speaking")
    speak(response, voice, gain)
    _emit(status_q, "status", "Idle")


# ── Loop runner (used by both CLI and the Tk panel) ───────────────────────────

def run_loop(state: RuntimeState, status_q: Queue | None = None) -> None:
    """Run conversation turns until state.stop is set or KeyboardInterrupt."""
    while not state.stop.is_set():
        try:
            run_voice_turn(state, status_q)
        except KeyboardInterrupt:
            _emit(status_q, "status", "Stopped")
            break
        except Exception as e:
            _emit(status_q, "error", str(e))
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
