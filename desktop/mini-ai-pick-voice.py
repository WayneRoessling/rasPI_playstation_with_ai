#!/usr/bin/env python3
"""
Mini-AI Voice & Volume Picker

GUI flow:
  1. Show a zenity radiolist of installed Piper voices (with descriptions)
  2. User picks one
  3. Optionally preview the chosen voice (synthesize a sample sentence)
  4. Show a zenity scale for the software volume gain (0.5 - 4.0)
  5. Save both choices to ~/.config/mini-ai/config.json

Falls back to a simple CLI menu when DISPLAY isn't set.

Exit codes:
  0 = saved (or no change)
  1 = cancelled or error
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

# Make sibling modules importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mini_ai_config import (
    VOICES, VOICES_BY_KEY, MIN_VOLUME_GAIN, MAX_VOLUME_GAIN, load_voice, save_voice, load_volume_gain, save_volume_gain,
    voice_model_path, voice_is_installed,
)

PIPER_BIN = os.path.expanduser("~/mini-ai/.venv/bin/piper")
SAMPLE_TEXT = (
    "Hello, I am Mini AI, a small voice and vision assistant running on a Raspberry Pi."
)


# ── Synthesis & playback ──────────────────────────────────────────────────────

def play_sample(voice_key: str, gain: float) -> None:
    """Synthesize a sample with the chosen voice + gain and play it."""
    voice = VOICES_BY_KEY[voice_key]
    if not voice_is_installed(voice):
        return
    raw = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    raw_path = raw.name
    raw.close()
    try:
        subprocess.run(
            [PIPER_BIN, "--model", voice_model_path(voice), "--output_file", raw_path],
            input=SAMPLE_TEXT, text=True, check=True, capture_output=True,
        )
        # Apply gain via ffmpeg if non-unity
        if abs(gain - 1.0) >= 0.01:
            amp_path = raw_path.replace(".wav", "_amp.wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", raw_path, "-filter:a", f"volume={gain}",
                 "-c:a", "pcm_s16le", amp_path],
                check=True, capture_output=True,
            )
            play_path = amp_path
        else:
            play_path = raw_path
        subprocess.run(["aplay", play_path], check=True, capture_output=True)
        if play_path != raw_path:
            try:
                os.unlink(play_path)
            except FileNotFoundError:
                pass
    finally:
        try:
            os.unlink(raw_path)
        except FileNotFoundError:
            pass


# ── GUI flow ──────────────────────────────────────────────────────────────────

def _zenity_pick_voice(current_key: str) -> str | None:
    rows: list[str] = []
    for v in VOICES:
        if not voice_is_installed(v):
            continue
        is_current = "TRUE" if v.key == current_key else "FALSE"
        rows.extend([is_current, v.key, v.label, v.description])
    if not rows:
        return None
    cmd = [
        "zenity", "--list", "--radiolist",
        "--title=Mini-AI Voice Picker",
        "--text=Choose a TTS voice (you can preview after):",
        "--width=720", "--height=360",
        "--column=Pick", "--column=Key", "--column=Voice", "--column=Description",
        "--hide-column=2", "--print-column=2",
        *rows,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _zenity_confirm_preview(voice_key: str) -> bool:
    voice = VOICES_BY_KEY[voice_key]
    cmd = [
        "zenity", "--question",
        "--title=Mini-AI Voice Preview",
        f"--text=Preview <b>{voice.label}</b>?\n\n(You'll hear a short sample.)",
        "--ok-label=Preview", "--cancel-label=Skip",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _zenity_pick_volume(current_gain: float) -> float | None:
    """Show a 0.5x..4.0x scale (rendered as 50..400 percent for usability)."""
    cmd = [
        "zenity", "--scale",
        "--title=Mini-AI Volume Gain",
        "--text=Software volume gain (100% = unchanged, 200% = +6dB).\n\nThe Pi's hardware volume is already at max.\nUse this for extra loudness on top.",
        f"--min-value={int(MIN_VOLUME_GAIN * 100)}",
        f"--max-value={int(MAX_VOLUME_GAIN * 100)}",
        f"--value={int(current_gain * 100)}",
        "--step=10",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip()) / 100.0
    except ValueError:
        return None


# ── CLI fallback ──────────────────────────────────────────────────────────────

def _cli_pick(current_voice: str, current_gain: float) -> tuple[str | None, float | None]:
    print()
    print("=" * 60)
    print("  Mini-AI Voice & Volume Picker")
    print("=" * 60)
    print()
    installed = [v for v in VOICES if voice_is_installed(v)]
    for i, v in enumerate(installed, start=1):
        marker = " *" if v.key == current_voice else "  "
        print(f"  {marker}{i}. {v.label}")
        print(f"        {v.description}")
        print()
    print("  q. Cancel")
    print()
    while True:
        try:
            choice = input(f"  Choose voice [1-{len(installed)}, default = current]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None, None
        if not choice:
            chosen_voice = current_voice
            break
        if choice == "q":
            return None, None
        if choice.isdigit() and 1 <= int(choice) <= len(installed):
            chosen_voice = installed[int(choice) - 1].key
            break
        print("  Invalid choice.")

    print()
    while True:
        try:
            raw = input(f"  Volume gain {MIN_VOLUME_GAIN}-{MAX_VOLUME_GAIN} [current {current_gain}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            return chosen_voice, None
        if not raw:
            return chosen_voice, current_gain
        try:
            return chosen_voice, float(raw)
        except ValueError:
            print("  Not a number.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    current_voice = load_voice().key
    current_gain = load_volume_gain()
    use_gui = bool(os.environ.get("DISPLAY")) and shutil.which("zenity")

    if use_gui:
        chosen_voice = _zenity_pick_voice(current_voice)
        if chosen_voice is None:
            print("Cancelled.", file=sys.stderr)
            return 1
        if _zenity_confirm_preview(chosen_voice):
            # Use the current saved gain for the preview (gain picker comes next)
            play_sample(chosen_voice, current_gain)
        chosen_gain = _zenity_pick_volume(current_gain)
        if chosen_gain is None:
            chosen_gain = current_gain  # user cancelled scale, keep old gain
    else:
        chosen_voice, chosen_gain = _cli_pick(current_voice, current_gain)
        if chosen_voice is None:
            return 1
        if chosen_gain is None:
            chosen_gain = current_gain

    save_voice(chosen_voice)
    save_volume_gain(chosen_gain)
    voice = VOICES_BY_KEY[chosen_voice]
    print(f"Saved voice: {voice.label}")
    print(f"Saved volume gain: {chosen_gain}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
