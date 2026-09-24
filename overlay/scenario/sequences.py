"""Background timed sequences for long-running scenario tools.

A countdown or a ramp that sleeps inside a tool blocks the LLM tool-use
loop for its whole duration: nothing else can happen (including a hold or
abort) until it finishes. Tools instead hand the timed part to ``start()``,
which runs it on a daemon thread and returns immediately. The body gets a
``cancelled`` event and paces itself with ``cancelled.wait(secs)`` so a
later tool (e.g. ``hold_countdown``) can stop it via ``cancel()``.

One sequence runs per panel (per HAL client): starting a new one cancels
whatever was running.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

log = logging.getLogger("scenario.sequences")

SequenceBody = Callable[[object, threading.Event], None]

_lock = threading.Lock()
# id(hal) -> (name, cancelled, thread)
_active: dict[int, tuple[str, threading.Event, threading.Thread]] = {}


def start(hal, name: str, body: SequenceBody) -> None:
    """Run ``body(hal, cancelled)`` in the background, replacing any active sequence."""
    cancel(hal)
    cancelled = threading.Event()

    def _run() -> None:
        try:
            body(hal, cancelled)
        except Exception:
            log.exception("sequence %r failed", name)
        finally:
            with _lock:
                entry = _active.get(id(hal))
                if entry is not None and entry[1] is cancelled:
                    del _active[id(hal)]

    thread = threading.Thread(target=_run, daemon=True, name=f"seq-{name}")
    with _lock:
        _active[id(hal)] = (name, cancelled, thread)
    thread.start()


def cancel(hal, wait: float = 1.0) -> Optional[str]:
    """Stop the active sequence on this panel; return its name, or None if idle.

    Waits up to ``wait`` seconds for the body to observe the cancel, so its
    in-flight step lands before the caller writes its own panel updates.
    """
    with _lock:
        entry = _active.pop(id(hal), None)
    if entry is None:
        return None
    name, cancelled, thread = entry
    cancelled.set()
    if thread is not threading.current_thread():
        thread.join(wait)
    return name


def active(hal) -> Optional[str]:
    """Name of the sequence running on this panel, or None."""
    with _lock:
        entry = _active.get(id(hal))
    return entry[0] if entry else None
