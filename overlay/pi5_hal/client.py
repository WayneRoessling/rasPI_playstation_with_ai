"""Thread-safe HAL client.

A background receive thread parses inbound JSON-lines frames, updates an
internal state mirror, dispatches to registered callbacks, and pushes
events onto a queue for synchronous consumers (`wait_for_event`).

Commands are sent synchronously from the caller's thread. Each command
gets an auto-assigned `id` so `ack` frames can be matched if desired.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any, Callable, Optional

log = logging.getLogger("pi5_hal")

# Event types that update peripheral state and get queued for waiters
INPUT_EVENT_TYPES = {"switch", "ptt", "pir", "key", "wake", "intent"}


class HalClient:
    def __init__(self, transport, *, history_size: int = 10):
        self.transport = transport
        self._history_size = history_size
        self._lock = threading.Lock()
        self._next_id = 1
        self._callbacks: dict[str, list[Callable[[dict], Any]]] = {}
        self._event_q: queue.Queue[dict] = queue.Queue()
        self._stop = threading.Event()
        self._rx_thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        # Outgoing-command recording — opt-in via start_recording(). When
        # not None, every cmd passed through send_raw() is appended. Used
        # by the scene harness in overlay/scenes/ to assert what tools
        # actually told the panel to do. None = recording off (default).
        self._record: Optional[list[dict]] = None
        # Mirror of the last write to each LCD line — populated whenever
        # write_lcd is called (or a hex frame is decoded). The scene
        # harness reads this for `lcd_line_N` assertions; nothing in the
        # production paths depends on it, so the additional state is
        # cheap.
        self._lcd: dict[int, str] = {1: "", 2: ""}
        self._state: dict[str, Any] = {
            "switches": [0] * 10,
            "ptt": 0,
            "pir": 0,
            "key": "SAFE",
            "wake": None,
            "intents": [],
            "leds_mirror": [0] * 50,  # mirror of last commanded LED state
            "caps": [],
            "fw": None,
            "connected": False,
        }

    # ── lifecycle ────────────────────────────────────────────────────────
    def connect(self, send_sync: bool = True, wait_ready: float = 1.0) -> None:
        self.transport.connect()
        with self._lock:
            self._state["connected"] = True
        self._stop.clear()
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True, name="hal-rx")
        self._rx_thread.start()
        if send_sync:
            self.sync()
            # Give the controller a moment to reply
            self._ready.wait(wait_ready)

    def disconnect(self) -> None:
        self._stop.set()
        try:
            self.transport.close()
        finally:
            with self._lock:
                self._state["connected"] = False
            # Join so a later connect() never has two rx threads racing on
            # the transport's queue. recv_line() polls every 0.5s.
            if self._rx_thread is not None and self._rx_thread is not threading.current_thread():
                self._rx_thread.join(timeout=2.0)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()

    # ── subscription ─────────────────────────────────────────────────────
    def on(self, type_: str, callback: Callable[[dict], Any]) -> None:
        """Register a callback for events with the given `t` field.
        Use `"*"` to subscribe to every frame.
        """
        with self._lock:
            self._callbacks.setdefault(type_, []).append(callback)

    def wait_for_event(self, type_filter: Optional[str] = None,
                       timeout: Optional[float] = None) -> Optional[dict]:
        """Block until an event matching `type_filter` arrives (or timeout).

        Drains other events into the void; use `on()` if you need every event.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            remaining = None
            if deadline is not None:
                remaining = max(0.0, deadline - time.monotonic())
                if remaining == 0:
                    return None
            try:
                msg = self._event_q.get(timeout=remaining)
            except queue.Empty:
                return None
            if type_filter is None or msg.get("t") == type_filter:
                return msg

    # ── state ────────────────────────────────────────────────────────────
    def state(self) -> dict:
        """Thread-safe snapshot of the state mirror."""
        with self._lock:
            return {
                "switches": list(self._state["switches"]),
                "ptt": self._state["ptt"],
                "pir": self._state["pir"],
                "key": self._state["key"],
                "wake": self._state["wake"],
                "intents": list(self._state["intents"]),
                "caps": list(self._state["caps"]),
                "fw": self._state["fw"],
                "connected": self._state["connected"],
            }

    def leds_mirror(self) -> list[int]:
        """Return a copy of the commanded LED state (0/1 per index 0..49)."""
        with self._lock:
            return list(self._state["leds_mirror"])

    def lcd_lines(self) -> dict[int, str]:
        """Return the last-commanded LCD line text by line number (1, 2)."""
        with self._lock:
            return dict(self._lcd)

    # ── recording (scene harness) ───────────────────────────────────────
    def start_recording(self) -> None:
        """Begin capturing every outgoing command in `pop_recording()`.

        Used by the Drop 7 scene harness in `overlay/scenes/` to assert
        what the runtime/LLM actually instructed the panel to do. Safe to
        call repeatedly — calling again resets the buffer.
        """
        with self._lock:
            self._record = []

    def stop_recording(self) -> None:
        """Disable command recording. Buffer is discarded."""
        with self._lock:
            self._record = None

    def pop_recording(self) -> list[dict]:
        """Return + clear the recorded commands since the last pop/start.

        Returns an empty list if recording is off. Each entry is the raw
        dict that went out over the wire, with `t` (the command type) and
        whatever per-command fields the dispatcher set (`id`, `text`,
        `slot`, …).
        """
        with self._lock:
            if self._record is None:
                return []
            buf = self._record
            self._record = []
            return buf

    # ── command convenience ─────────────────────────────────────────────
    def _next(self) -> int:
        with self._lock:
            n = self._next_id
            self._next_id += 1
            return n

    def send_raw(self, cmd: dict) -> int:
        # `led` uses `id` for the LED number, so its tracking id (the value
        # echoed back as ack.of) travels as `id_msg` — HAL_PROTOCOL.md §5.1.
        key = "id_msg" if cmd.get("t") == "led" else "id"
        if key not in cmd:
            cmd[key] = self._next()
        # Tap the recorder before the transport write so a transient
        # transport error still leaves a complete audit trail.
        with self._lock:
            if self._record is not None:
                self._record.append(dict(cmd))
        self.transport.send(json.dumps(cmd))
        return cmd[key]

    def set_led(self, led_id: int, on: bool = True, brightness: Optional[int] = None) -> int:
        v = brightness if brightness is not None else (255 if on else 0)
        with self._lock:
            if 1 <= led_id <= 50:
                self._state["leds_mirror"][led_id - 1] = 1 if v >= 128 else 0
        return self.send_raw({"t": "led", "id": led_id, "v": int(v)})

    def set_leds(self, values: str, format: str = "hex_pairs") -> int:
        return self.send_raw({"t": "leds", "values": values, "format": format})

    def clear_leds(self) -> int:
        with self._lock:
            self._state["leds_mirror"] = [0] * 50
        return self.set_leds("00" * 50, "hex_pairs")

    def write_lcd(self, line: int, text: str) -> int:
        line_i = int(line)
        text_s = str(text)
        with self._lock:
            if line_i in (1, 2):
                self._lcd[line_i] = text_s
        return self.send_raw({"t": "lcd", "line": line_i, "text": text_s})

    def clear_lcd(self) -> int:
        with self._lock:
            self._lcd = {1: "", 2: ""}
        return self.send_raw({"t": "lcd_clear"})

    def render_oled(self, display: str, layout: str, data: dict) -> int:
        return self.send_raw({
            "t": "oled", "display": display, "layout": layout, "data": data
        })

    def play_sfx(self, slot: int, pulse_ms: int = 100) -> int:
        return self.send_raw({"t": "sfx", "slot": int(slot), "pulse_ms": int(pulse_ms)})

    def play_sfx_seq(self, slot: int, count: int, interval_ms: int = 1000) -> int:
        return self.send_raw({
            "t": "sfx_seq", "slot": int(slot),
            "count": int(count), "interval_ms": int(interval_ms),
        })

    def sync(self) -> int:
        return self.send_raw({"t": "sync"})

    def reset(self) -> int:
        return self.send_raw({"t": "reset"})

    # ── internal: receive loop ──────────────────────────────────────────
    def _rx_loop(self) -> None:
        while not self._stop.is_set():
            line = self.transport.recv_line(timeout=0.5)
            if not line:
                # Transports without a `connected` attribute are assumed up.
                if not getattr(self.transport, "connected", True):
                    if not self._stop.is_set():   # a deliberate disconnect() isn't news
                        log.warning("HAL transport disconnected")
                    with self._lock:
                        self._state["connected"] = False
                    return
                continue
            try:
                msg = json.loads(line)
            except (ValueError, TypeError):
                log.warning("dropped bad json (%d bytes)", len(line))
                continue
            if not isinstance(msg, dict) or "t" not in msg:
                continue
            self._dispatch(msg)

    def _dispatch(self, msg: dict) -> None:
        t = msg.get("t")
        # Update state mirror
        with self._lock:
            if t == "switch":
                idx = int(msg.get("id", 0)) - 1
                if 0 <= idx < 10:
                    self._state["switches"][idx] = int(msg.get("state", 0))
            elif t == "ptt":
                self._state["ptt"] = int(msg.get("state", 0))
            elif t == "pir":
                self._state["pir"] = int(msg.get("state", 0))
            elif t == "key":
                self._state["key"] = str(msg.get("pos", "SAFE"))
            elif t == "wake":
                self._state["wake"] = {
                    "word": msg.get("word"), "conf": msg.get("conf"), "ms": msg.get("ms"),
                }
            elif t == "intent":
                rec = {
                    "key": msg.get("key"), "conf": msg.get("conf"), "ms": msg.get("ms"),
                }
                hist = self._state["intents"] + [rec]
                self._state["intents"] = hist[-self._history_size:]
            elif t == "hello":
                self._state["fw"] = msg.get("fw")
                self._state["caps"] = list(msg.get("caps", []))
            elif t == "ready":
                self._ready.set()
            callbacks = list(self._callbacks.get(t, []))
            wildcards = list(self._callbacks.get("*", []))

        # Dispatch outside the lock
        for cb in callbacks + wildcards:
            try:
                cb(msg)
            except Exception as e:
                log.warning("callback for %s raised: %r", t, e)
        # Queue input events for synchronous waiters
        if t in INPUT_EVENT_TYPES:
            self._event_q.put(msg)
