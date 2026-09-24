#!/usr/bin/env python3
"""
Mini-AI Model Picker
Shows a zenity GUI dialog (with CLI fallback) so the desktop user can
swap between TINY / FAST / SMART model presets without editing code.

Saves the chosen preset to ~/.config/mini-ai/config.json. The next launch
of voice_pipeline.py will read it via mini_ai_config.load_preset().

Exit codes:
  0 = preset selected and saved
  1 = user cancelled or error
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

# Make sibling modules importable when launched from anywhere
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mini_ai_config import PRESETS, PRESETS_BY_KEY, DEFAULT_PRESET_KEY, load_preset, save_preset


def _zenity_pick(current_key: str) -> str | None:
    """Show a zenity radio list. Returns chosen key or None on cancel."""
    rows: list[str] = []
    for p in PRESETS:
        is_current = "TRUE" if p.key == current_key else "FALSE"
        rows.extend([is_current, p.key, p.label, p.description])

    cmd = [
        "zenity", "--list", "--radiolist",
        "--title=Mini-AI Model Picker",
        "--text=Choose a model preset (faster = less smart):",
        "--width=720", "--height=320",
        "--column=Pick", "--column=Key", "--column=Preset", "--column=Description",
        "--hide-column=2", "--print-column=2",
        *rows,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None  # user clicked Cancel
    chosen = result.stdout.strip()
    return chosen or None


def _cli_pick(current_key: str) -> str | None:
    """Numbered text menu fallback when zenity is unavailable."""
    print()
    print("=" * 60)
    print("  Mini-AI Model Picker")
    print("=" * 60)
    print()
    for i, p in enumerate(PRESETS, start=1):
        marker = " *" if p.key == current_key else "  "
        print(f"  {marker}{i}. {p.label}")
        print(f"        text:   {p.text_model}")
        print(f"        vision: {p.vision_model}")
        print(f"        {p.description}")
        print()
    print("  q. Cancel")
    print()
    while True:
        try:
            choice = input(f"  Choose [1-{len(PRESETS)}, default = current]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if not choice:
            return current_key
        if choice == "q":
            return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(PRESETS):
                return PRESETS[idx].key
        print("  Invalid choice, try again.")


def main() -> int:
    current = load_preset()
    current_key = current.key.split("+")[0]  # strip "+override" suffix if any
    if current_key not in PRESETS_BY_KEY:
        current_key = DEFAULT_PRESET_KEY

    use_gui = bool(os.environ.get("DISPLAY")) and shutil.which("zenity")
    chosen_key = _zenity_pick(current_key) if use_gui else _cli_pick(current_key)

    if chosen_key is None:
        print("Cancelled — keeping current preset.", file=sys.stderr)
        return 1

    if chosen_key == current_key:
        print(f"No change — already on '{chosen_key}'.", file=sys.stderr)
        return 0

    save_preset(chosen_key)
    p = PRESETS_BY_KEY[chosen_key]
    print(f"Saved preset: {p.label}")
    print(f"  text:   {p.text_model}")
    print(f"  vision: {p.vision_model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
