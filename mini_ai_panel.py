#!/usr/bin/env python3
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
  │  Mode:    [Pirate Space Ship                ▼]   │
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
  │  ┌ Mic sensitivity ────────────────────────────┐│
  │  │ [x] Auto (adjusts to room noise)            ││
  │  │ Sensitivity: ├────●──────┤  70%  (thr 1270) ││
  │  │ Pause to finish: ├──●────┤  0.8 s           ││
  │  │ Mic level: ▓▓▓▓▓▓░░░░│░░░░░  820 / 450      ││
  │  └─────────────────────────────────────────────┘│
  │                                                 │
  │  Preset: FAST  •  llama3.2:1b + moondream       │
  │                                                 │
  │  [ Test voice ]                       [ Quit ]  │
  └─────────────────────────────────────────────────┘
"""
from __future__ import annotations

import math
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
    MIN_VAD_THRESHOLD, MAX_VAD_THRESHOLD, VAD_THRESHOLD_AUTO,
    MIN_VAD_SILENCE_MS, MAX_VAD_SILENCE_MS,
    save_voice, save_volume_gain, save_personality,
    save_vad_threshold, save_vad_silence_ms, save_scenario,
    voice_is_installed,
)
from voice_pipeline import (
    RuntimeState, make_default_state, run_loop, speak,
)


SAMPLE_TEXT = "Hello, I am Mini AI. This is a test of the current voice and volume."

VOICE_MODE_LABEL = "Voice assistant (no panel)"


def load_mode_choices() -> tuple[list[tuple[str, str | None]], str | None]:
    """[(label, scenario_id or None)] for the Mode picker, plus an error if
    the scenarios couldn't be loaded (overlay deps missing, bad YAML...)."""
    choices: list[tuple[str, str | None]] = [(VOICE_MODE_LABEL, None)]
    try:
        from overlay.scenario.demo import SCENARIOS
    except Exception as e:   # the plain assistant must keep working without overlay/
        return choices, f"Scenarios unavailable: {e}"
    scenarios = [(f"Scenario: {sc.name}", sid) for sid, sc in SCENARIOS.items() if sid != "test_console"]
    if "test_console" in SCENARIOS:
        scenarios.append(("Diagnostics: Test Console", "test_console"))
    return choices + scenarios, None

# Manual sensitivity used when "Auto" is first switched off.
DEFAULT_MANUAL_THRESHOLD = 800.0
# Mic meter spans this RMS range on a log scale (speech is ~300-5000).
METER_MIN_RMS, METER_MAX_RMS = 30.0, 8000.0
METER_W, METER_H = 260, 14


def sensitivity_to_threshold(pct: float) -> float:
    """0% = least sensitive (highest threshold) … 100% = most sensitive."""
    return MAX_VAD_THRESHOLD - (pct / 100.0) * (MAX_VAD_THRESHOLD - MIN_VAD_THRESHOLD)


def threshold_to_sensitivity(threshold: float) -> float:
    return 100.0 * (MAX_VAD_THRESHOLD - threshold) / (MAX_VAD_THRESHOLD - MIN_VAD_THRESHOLD)


def _meter_x(rms: float) -> float:
    rms = min(max(rms, METER_MIN_RMS), METER_MAX_RMS)
    return METER_W * math.log(rms / METER_MIN_RMS) / math.log(METER_MAX_RMS / METER_MIN_RMS)


# ── GUI ──────────────────────────────────────────────────────────────────────

class ControlPanel:
    def __init__(self, root: tk.Tk, state: RuntimeState, status_q: Queue) -> None:
        self.root = root
        self.state = state
        self.status_q = status_q
        self._test_thread: threading.Thread | None = None

        root.title("Mini-AI Controls")
        root.geometry("560x700")
        root.minsize(520, 660)

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

        # Mode picker (live): plain assistant or one of the console scenarios
        mode_row = ttk.Frame(outer)
        mode_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(mode_row, text="Mode:", width=10).pack(side=tk.LEFT)
        self.mode_choices, mode_error = load_mode_choices()
        labels = [label for label, _ in self.mode_choices]
        current = state.current_scenario()
        current_label = next((label for label, sid in self.mode_choices if sid == current), None)
        if current_label is None:     # saved/env scenario not loadable — show it anyway
            current_label = f"Scenario: {current}"
            self.mode_choices.append((current_label, current))
            labels.append(current_label)
        self.mode_var = tk.StringVar(value=current_label)
        mode_combo = ttk.Combobox(mode_row, textvariable=self.mode_var, values=labels,
                                  state="readonly", width=36)
        mode_combo.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)
        if mode_error:
            ttk.Label(outer, text=mode_error, foreground="#b3261e", font=("", 8),
                      wraplength=480).pack(anchor=tk.W)
        self.mode_hint = ttk.Label(outer, foreground="#666", font=("", 8), wraplength=480)
        self.mode_hint.pack(anchor=tk.W)
        self._refresh_mode_hint()

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

        self._build_mic_sensitivity(outer, state)

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

    def _refresh_mode_hint(self) -> None:
        if self.state.current_scenario():
            self.mode_hint.config(text="Hold the panel's push-to-talk button to speak. "
                                       "Switch modes any time; the change applies after "
                                       "the current turn.")
        else:
            self.mode_hint.config(text="Just talk — it listens and answers. "
                                       "Pick a scenario to drive the console instead.")

    def _on_mode_change(self, _event=None) -> None:
        label = self.mode_var.get()
        scenario_id = next((sid for lab, sid in self.mode_choices if lab == label), None)
        self.state.set_scenario(scenario_id)
        save_scenario(scenario_id)
        self._refresh_mode_hint()
        self.status_var.set("Switching mode…")

    def _build_mic_sensitivity(self, parent: ttk.Frame, state: RuntimeState) -> None:
        """Speech threshold + end-of-utterance pause, with a live mic meter."""
        threshold, silence_ms = state.vad_settings()
        box = ttk.LabelFrame(parent, text="Mic sensitivity (voice mode)", padding=8)
        box.pack(fill=tk.X, pady=(10, 0))

        self.vad_auto_var = tk.BooleanVar(value=threshold == VAD_THRESHOLD_AUTO)
        ttk.Checkbutton(
            box, text="Auto (adjusts to room noise each time it listens)",
            variable=self.vad_auto_var, command=self._on_vad_auto_toggle,
        ).pack(anchor=tk.W)

        sens_row = ttk.Frame(box)
        sens_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(sens_row, text="Sensitivity:", width=14).pack(side=tk.LEFT)
        manual = threshold if threshold != VAD_THRESHOLD_AUTO else DEFAULT_MANUAL_THRESHOLD
        self.sens_var = tk.DoubleVar(value=threshold_to_sensitivity(manual))
        self.sens_scale = ttk.Scale(
            sens_row, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self.sens_var, command=self._on_sensitivity_change,
        )
        self.sens_scale.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        self.sens_label = ttk.Label(sens_row, width=16)
        self.sens_label.pack(side=tk.LEFT)

        pause_row = ttk.Frame(box)
        pause_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(pause_row, text="Pause to finish:", width=14).pack(side=tk.LEFT)
        self.pause_var = tk.DoubleVar(value=silence_ms)
        ttk.Scale(
            pause_row, from_=MIN_VAD_SILENCE_MS, to=MAX_VAD_SILENCE_MS, orient=tk.HORIZONTAL,
            variable=self.pause_var, command=self._on_pause_change,
        ).pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        self.pause_label = ttk.Label(pause_row, text=f"{silence_ms / 1000:.1f} s", width=16)
        self.pause_label.pack(side=tk.LEFT)

        meter_row = ttk.Frame(box)
        meter_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(meter_row, text="Mic level:", width=14).pack(side=tk.LEFT)
        self.meter = tk.Canvas(meter_row, width=METER_W, height=METER_H,
                               background="#e8e8e8", highlightthickness=0)
        self.meter.pack(side=tk.LEFT, padx=(4, 8))
        self.meter_bar = self.meter.create_rectangle(0, 0, 0, METER_H, fill="#34a853", width=0)
        self.meter_mark = self.meter.create_line(0, 0, 0, METER_H, fill="#d93025", width=2)
        self.meter_label = ttk.Label(meter_row, text="(while listening)", width=16)
        self.meter_label.pack(side=tk.LEFT)

        ttk.Label(
            box, foreground="#666", font=("", 8), wraplength=460, justify=tk.LEFT,
            text=("While it's listening, talk normally: the green bar should cross the red "
                  "line when you speak and fall below it when you stop. Cut off mid-sentence? "
                  "Raise 'Pause to finish'. Not hearing you? Turn Auto off and raise "
                  "Sensitivity. Picking up background noise? Lower it."),
        ).pack(anchor=tk.W, pady=(6, 0))

        self._refresh_sensitivity_widgets()

    def _refresh_sensitivity_widgets(self) -> None:
        auto = self.vad_auto_var.get()
        self.sens_scale.state(["disabled"] if auto else ["!disabled"])
        if auto:
            self.sens_label.config(text="auto")
        else:
            pct = self.sens_var.get()
            self.sens_label.config(text=f"{pct:.0f}%  (thr {sensitivity_to_threshold(pct):.0f})")

    def _on_vad_auto_toggle(self) -> None:
        if self.vad_auto_var.get():
            threshold = VAD_THRESHOLD_AUTO
        else:
            threshold = sensitivity_to_threshold(self.sens_var.get())
        self.state.set_vad_threshold(threshold)
        save_vad_threshold(threshold)
        self._refresh_sensitivity_widgets()

    def _on_sensitivity_change(self, _value=None) -> None:
        if self.vad_auto_var.get():
            return
        threshold = sensitivity_to_threshold(self.sens_var.get())
        self.state.set_vad_threshold(threshold)
        save_vad_threshold(threshold)
        self._refresh_sensitivity_widgets()

    def _on_pause_change(self, _value=None) -> None:
        silence_ms = int(round(self.pause_var.get() / 100.0) * 100)   # 0.1 s steps
        self.pause_label.config(text=f"{silence_ms / 1000:.1f} s")
        self.state.set_vad_silence_ms(silence_ms)
        save_vad_silence_ms(silence_ms)

    def _show_level(self, rms: float, threshold: float) -> None:
        x = _meter_x(rms)
        self.meter.coords(self.meter_bar, 0, 0, x, METER_H)
        self.meter.itemconfig(self.meter_bar, fill="#34a853" if rms >= threshold else "#9aa0a6")
        mark = _meter_x(threshold)
        self.meter.coords(self.meter_mark, mark, 0, mark, METER_H)
        self.meter_label.config(text=f"{rms:.0f} / {threshold:.0f}")

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
        _, _, voice, gain, _ = self.state.snapshot()

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
                elif kind == "level":
                    rms, threshold = (float(v) for v in text.split())
                    self._show_level(rms, threshold)
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
