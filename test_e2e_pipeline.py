#!/usr/bin/env python3
"""End-to-end pipeline test -- exercises each component without live mic input."""
import sys
import time
import subprocess
import os

sys.path.insert(0, "/home/miniai_admin/mini-ai")
from voice_pipeline import transcribe, ask_llm, capture_image
from mini_ai_config import load_preset

# Resolve current models from saved config so the test exercises the active preset
_PRESET = load_preset()
TEXT_MODEL = _PRESET.text_model
VISION_MODEL = _PRESET.vision_model

HOME = os.path.expanduser("~")
PIPER_BIN = os.path.join(HOME, "mini-ai/.venv/bin/piper")
PIPER_MODEL = os.path.join(HOME, "piper-voices/en_US-lessac-medium.onnx")

print("=" * 50)
print("  Mini-AI E2E Pipeline Test")
print("=" * 50)

print()
print("[1/5] TTS - generating test audio...")
t0 = time.time()
subprocess.run(
    [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", "/tmp/e2e_test.wav"],
    input="What is the capital of France?",
    text=True, check=True, capture_output=True,
)
print(f"  OK - {time.time()-t0:.1f}s")

subprocess.run(
    ["ffmpeg", "-y", "-i", "/tmp/e2e_test.wav",
     "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "/tmp/e2e_test_16k.wav"],
    check=True, capture_output=True,
)

print("[2/5] STT - transcribing audio...")
t0 = time.time()
text = transcribe("/tmp/e2e_test_16k.wav")
print(f"  Transcript: {text!r}")
print(f"  OK - {time.time()-t0:.1f}s")

print(f"[3/5] LLM - text inference ({TEXT_MODEL})...")
t0 = time.time()
response = ask_llm(text, TEXT_MODEL, VISION_MODEL)
print(f"  Response: {response[:200]!r}")
print(f"  OK - {time.time()-t0:.1f}s")

print(f"[4/5] Vision - camera capture + {VISION_MODEL}...")
t0 = time.time()
img = capture_image()
vision_resp = ask_llm("Describe this image briefly.", TEXT_MODEL, VISION_MODEL, image_path=img)
os.unlink(img)
print(f"  Vision: {vision_resp[:200]!r}")
print(f"  OK - {time.time()-t0:.1f}s")

print("[5/5] TTS - speaking response...")
t0 = time.time()
subprocess.run(
    [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", "/tmp/e2e_resp.wav"],
    input=response[:100],
    text=True, check=True, capture_output=True,
)
print(f"  OK - {time.time()-t0:.1f}s")

print()
print("=" * 50)
print("  ALL E2E TESTS PASSED")
print("=" * 50)

for f in ["/tmp/e2e_test.wav", "/tmp/e2e_test_16k.wav", "/tmp/e2e_resp.wav"]:
    if os.path.exists(f):
        os.unlink(f)
