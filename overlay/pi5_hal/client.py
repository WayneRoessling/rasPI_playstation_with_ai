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

    # ── command convenience ─────────────────────────────────────────────
    def _next(self) -> int:
        with self._lock:
            n = self._next_id
            self._next_id += 1
            return n

    def send_raw(self, cmd: dict) -> int:
        if "id" not in cmd:
            cmd["id"] = self._next()
        self.transport.send(json.dumps(cmd))
        return cmd["id"]

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
        return self.send_raw({"t": "lcd", "line": int(line), "text": str(text)})

    def clear_lcd(self) -> int:
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
