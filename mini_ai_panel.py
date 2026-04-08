#!/home/miniai_admin/mini-ai/.venv/bin/python3
"""
Mini-AI Live Control Panel

A small Tkinter window that runs the voice pipeline in a background thread
and lets the user change voice and volume on the fly. The voice loop reads
the live RuntimeState on every turn, so changes take effect on the next
spoken response with no restart needed.

Layout:

  ┌─ Mini-AI Controls ─────────────────────────────┐
  │                                                 │
  │  ●  Listening (5s)                              │
  │                                                 │
  │  You said:                                      │
  │  ┌────────────────────────────────────────────┐ │
  │  │ What is the capital of France?             │ │
  │  └────────────────────────────────────────────┘ │
  │                                                 │
  │  Assistant:                                     │
  │  ┌────────────────────────────────────────────┐ │
  │  │ The capital of France is Paris.            │ │
  │  └────────────────────────────────────────────┘ │
  │                                                 │
  │  Voice:   [Lessac (US female, neutral)     ▼]   │
  │  Volume:  ├──●─────────────┤   150%             │
  │                                                 │
  │  Preset: FAST  •  llama3.2:1b + moondream       │
  │                                                 │
  │  [ Test voice ]                       [ Quit ]  │
  └─────────────────────────────────────────────────┘
"""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from queue import Queue, Empty
from tkinter import ttk

# Make sibling modules importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mini_ai_config import (
    VOICES, VOICES_BY_KEY,
    PERSONALITIES, PERSONALITIES_BY_KEY,
    MIN_VOLUME_GAIN, MAX_VOLUME_GAIN,
    save_voice, save_volume_gain, save_personality,
    voice_is_installed,
)
from voice_pipeline import (
    RuntimeState, make_default_state, run_loop, speak,
)


SAMPLE_TEXT = "Hello, I am Mini AI. This is a test of the current voice and volume."


# ── GUI ──────────────────────────────────────────────────────────────────────

class ControlPanel:
    def __init__(self, root: tk.Tk, state: RuntimeState, status_q: Queue) -> None:
        self.root = root
        self.state = state
        self.status_q = status_q
        self._test_thread: threading.Thread | None = None

        root.title("Mini-AI Controls")
        root.geometry("520x440")
        root.minsize(480, 420)

        # Outer padding
        outer = ttk.Frame(root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        # Status badge
        self.status_var = tk.StringVar(value="Starting")
        status_row = ttk.Frame(outer)
        status_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(status_row, text="Status:", font=("", 10, "bold")).pack(side=tk.LEFT)
        self.status_label = ttk.Label(
            status_row, textvariable=self.status_var,
            font=("", 10), foreground="#1a73e8",
        )
        self.status_label.pack(side=tk.LEFT, padx=(8, 0))

        # User said
        ttk.Label(outer, text="You said:", font=("", 9, "bold")).pack(anchor=tk.W, pady=(4, 2))
        self.user_text = tk.Text(outer, height=2, wrap=tk.WORD, state=tk.DISABLED,
                                 background="#f5f5f5", relief=tk.FLAT, padx=6, pady=4)
        self.user_text.pack(fill=tk.X)

        # Assistant
        ttk.Label(outer, text="Assistant:", font=("", 9, "bold")).pack(anchor=tk.W, pady=(8, 2))
        self.asst_text = tk.Text(outer, height=4, wrap=tk.WORD, state=tk.DISABLED,
                                 background="#eef5ff", relief=tk.FLAT, padx=6, pady=4)
        self.asst_text.pack(fill=tk.X)

        # Voice picker (live)
        voice_row = ttk.Frame(outer)
        voice_row.pack(fill=tk.X, pady=(12, 4))
        ttk.Label(voice_row, text="Voice:", width=10).pack(side=tk.LEFT)
        installed_voices = [v for v in VOICES if voice_is_installed(v)]
        self.voice_labels = [v.label for v in installed_voices]
        self.label_to_key = {v.label: v.key for v in installed_voices}
        self.voice_var = tk.StringVar(value=state.voice.label)
        self.voice_combo = ttk.Combobox(
            voice_row, textvariable=self.voice_var,
            values=self.voice_labels, state="readonly", width=36,
        )
        self.voice_combo.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        self.voice_combo.bind("<<ComboboxSelected>>", self._on_voice_change)

        # Personality picker (live)
        personality_row = ttk.Frame(outer)
        personality_row.pack(fill=tk.X, pady=(8, 4))
        ttk.Label(personality_row, text="Personality:", width=10).pack(side=tk.LEFT)
        self.personality_labels = [p.label for p in PERSONALITIES]
        self.label_to_personality_key = {p.label: p.key for p in PERSONALITIES}
        self.personality_var = tk.StringVar(value=state.personality.label)
        self.personality_combo = ttk.Combobox(
            personality_row, textvariable=self.personality_var,
            values=self.personality_labels, state="readonly", width=36,
        )
        self.personality_combo.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        self.personality_combo.bind("<<ComboboxSelected>>", self._on_personality_change)

        # Volume slider (live)
        vol_row = ttk.Frame(outer)
        vol_row.pack(fill=tk.X, pady=(8, 4))
        ttk.Label(vol_row, text="Volume:", width=10).pack(side=tk.LEFT)
        self.vol_var = tk.DoubleVar(value=state.volume_gain * 100)
        self.vol_scale = ttk.Scale(
            vol_row, from_=MIN_VOLUME_GAIN * 100, to=MAX_VOLUME_GAIN * 100,
            orient=tk.HORIZONTAL, variable=self.vol_var,
            command=self._on_volume_change,
        )
        self.vol_scale.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        self.vol_label = ttk.Label(vol_row, text=f"{int(state.volume_gain * 100)}%", width=6)
        self.vol_label.pack(side=tk.LEFT)

        # Preset display (read-only here; change it via the model picker)
        preset_text = (
            f"Preset: {os.path.basename(state.text_model)} (text)  •  "
            f"{os.path.basename(state.vision_model)} (vision)"
        )
        ttk.Label(outer, text=preset_text, font=("", 8), foreground="#666").pack(
            anchor=tk.W, pady=(8, 0)
        )

        # Buttons
        btn_row = ttk.Frame(outer)
        btn_row.pack(fill=tk.X, pady=(14, 0))
        self.test_btn = ttk.Button(btn_row, text="Test voice", command=self._on_test_voice)
        self.test_btn.pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Quit", command=self._on_quit).pack(side=tk.RIGHT)

        # Wire window-close to quit cleanly
        root.protocol("WM_DELETE_WINDOW", self._on_quit)

        # Start polling the status queue
        root.after(150, self._drain_status_queue)

    # ── Widget callbacks ──────────────────────────────────────────────────────

    def _on_voice_change(self, _event=None) -> None:
        label = self.voice_var.get()
        key = self.label_to_key.get(label)
        if not key:
            return
        voice = VOICES_BY_KEY[key]
        self.state.set_voice(voice)
        save_voice(key)

    def _on_personality_change(self, _event=None) -> None:
        label = self.personality_var.get()
        key = self.label_to_personality_key.get(label)
        if not key:
            return
        self.state.set_personality(PERSONALITIES_BY_KEY[key])
        save_personality(key)

    def _on_volume_change(self, _value=None) -> None:
        gain = self.vol_var.get() / 100.0
        self.vol_label.config(text=f"{int(self.vol_var.get())}%")
        self.state.set_volume(gain)
        # Persist immediately so headless launches see the same value
        save_volume_gain(gain)

    def _on_test_voice(self) -> None:
        """Synthesize the sample sentence with the current voice + gain."""
        if self._test_thread is not None and self._test_thread.is_alive():
            return
        self.test_btn.config(state=tk.DISABLED)
        _, _, voice, gain = self.state.snapshot()

        def _run() -> None:
            try:
                speak(SAMPLE_TEXT, voice, gain)
            except Exception as e:
                self.status_q.put(("error", f"Test voice failed: {e}"))
            finally:
                self.root.after(0, lambda: self.test_btn.config(state=tk.NORMAL))

        self._test_thread = threading.Thread(target=_run, daemon=True)
        self._test_thread.start()

    def _on_quit(self) -> None:
        """Signal the loop to stop and tear down the GUI."""
        self.state.stop.set()
        self.root.after(100, self.root.destroy)

    # ── Status queue polling ──────────────────────────────────────────────────

    def _drain_status_queue(self) -> None:
        """Pull pending status events from the loop thread and update widgets."""
        try:
            while True:
                kind, text = self.status_q.get_nowait()
                if kind == "status":
                    self.status_var.set(text)
                elif kind == "user":
                    self._set_text(self.user_text, text)
                elif kind == "asst":
                    self._set_text(self.asst_text, text)
                elif kind == "error":
                    self.status_var.set("ERROR — see assistant box")
                    self._set_text(self.asst_text, f"ERROR:\n{text}")
        except Empty:
            pass
        # Re-arm
        self.root.after(150, self._drain_status_queue)

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.config(state=tk.DISABLED)


# ── Entrypoint ───────────────────────────────────────────────────────────────

def main() -> int:
    state = make_default_state()
    status_q: Queue = Queue()

    # Voice loop in a daemon thread
    loop_thread = threading.Thread(
        target=run_loop, args=(state, status_q), daemon=True,
    )
    loop_thread.start()

    # Tk on the main thread
    root = tk.Tk()
    ControlPanel(root, state, status_q)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        state.stop.set()

    # Allow the loop thread to wind down (it checks stop between turns,
    # but a turn in progress can take a while — daemon=True is the safety net)
    state.stop.set()
    loop_thread.join(timeout=2.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
