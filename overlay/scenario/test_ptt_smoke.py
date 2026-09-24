"""Smoke test for the streaming-PTT subprocess management logic.

We don't have audio hardware in the test environment, so this exercises
``voice_pipeline._record_ptt_gated`` against a mock HAL + mock arecord
subprocess. Verifies:

1. Recording starts only after a PTT-press edge is observed.
2. Recording stops on PTT-release edge (the common path).
3. Recording also stops on the safety cap (a stuck-PTT scenario).
4. ``_stop_arecord`` is called exactly once per session.

Run::

    python -m overlay.scenario.test_ptt_smoke

(This is intentionally a standalone script, not a pytest module, to
avoid pulling pytest into the overlay deps. It prints `PASS` or
exits non-zero.)
"""

from __future__ import annotations

import sys
import tempfile
import time
import threading
import types
from pathlib import Path
from unittest import mock


# Ensure repo root is on sys.path so `voice_pipeline` is importable
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# voice_pipeline.py imports cv2 (for vision); we stub it so this smoke
# test runs in environments without OpenCV — we never exercise the vision
# path here.
if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.SimpleNamespace(
        VideoCapture=lambda *a, **k: None,
        CAP_PROP_FRAME_WIDTH=0,
        CAP_PROP_FRAME_HEIGHT=0,
        imwrite=lambda *a, **k: True,
    )


class FakeProc:
    """Stand-in for subprocess.Popen — never really running."""

    def __init__(self):
        self._terminated = False
        self.returncode = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls = 0

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminate_calls += 1
        self._terminated = True
        self.returncode = 0

    def kill(self):
        self.kill_calls += 1
        self._terminated = True
        self.returncode = -9

    def wait(self, timeout=None):
        self.wait_calls += 1
        return self.returncode


class FakeHal:
    """Minimal HAL stand-in: emits PTT events on a tiny event queue.

    The real HalClient exposes `.state()` and `.wait_for_event(kind, timeout)`.
    We approximate both — `.state()` reflects the current ptt level, and
    `.wait_for_event` blocks (briefly) for the next queued event.
    """

    def __init__(self):
        import queue
        self._ptt = 0
        self._q: "queue.Queue[dict]" = queue.Queue()

    def state(self):
        return {"ptt": self._ptt}

    def wait_for_event(self, kind, timeout):
        import queue as _q
        if kind != "ptt":
            return None
        try:
            evt = self._q.get(timeout=timeout)
        except _q.Empty:
            return None
        return evt

    def press(self):
        self._ptt = 1
        self._q.put({"t": "ptt", "state": 1})

    def release(self):
        self._ptt = 0
        self._q.put({"t": "ptt", "state": 0})


def _run_one(safety_cap_secs: float, release_after: float | None,
             max_wait: float) -> tuple[FakeProc, float, str | None]:
    """Run one _record_ptt_gated invocation against a FakeHal.

    Returns (proc, elapsed_seconds, returned_path).
    """
    import voice_pipeline as vp

    hal = FakeHal()
    proc = FakeProc()

    started = threading.Event()

    def fake_start_arecord(card, out_path):
        started.set()
        # Create an empty file so the resample step can be skipped if we
        # short-circuit, but for this smoke we'll mock ffmpeg too.
        Path(out_path).write_bytes(b"")
        return proc

    def driver():
        # Wait until the loop is "waiting for PTT", then press, optionally
        # wait release_after seconds, then release.
        # We approximate "loop is waiting" by waiting on `started` plus a
        # short sleep — the loop blocks on hal.wait_for_event before press.
        hal.press()
        if release_after is None:
            return                  # never release (safety-cap path)
        time.sleep(release_after)
        hal.release()

    t = threading.Thread(target=driver, daemon=True)
    t.start()

    with mock.patch.object(vp, "_start_arecord", side_effect=fake_start_arecord), \
         mock.patch.object(vp, "_stop_arecord", side_effect=lambda p: p.terminate()), \
         mock.patch.object(vp, "_get_audio_card", return_value="plughw:CARD=Test,DEV=0"), \
         mock.patch.object(vp.subprocess, "run", return_value=mock.Mock(returncode=0)), \
         mock.patch.object(vp.os, "unlink"), \
         mock.patch.object(vp.tempfile, "NamedTemporaryFile") as mtmp:
        # Make NamedTemporaryFile return an object with a .name we control
        fake_file = mock.Mock()
        fake_file.name = tempfile.gettempdir() + "/fake_ptt_smoke.wav"
        fake_file.close = lambda: None
        mtmp.return_value = fake_file

        t0 = time.monotonic()
        out = vp._record_ptt_gated(hal, status_q=None, max_secs=int(safety_cap_secs))
        elapsed = time.monotonic() - t0

    return proc, elapsed, out


def test_release_path():
    """Press, hold for 0.3s, release — should stop within ~0.5s and
    call terminate exactly once."""
    proc, elapsed, out = _run_one(safety_cap_secs=10.0,
                                  release_after=0.3,
                                  max_wait=2.0)
    assert proc.terminate_calls == 1, f"terminate calls: {proc.terminate_calls}"
    assert proc.kill_calls == 0, f"unexpected kill: {proc.kill_calls}"
    # Recording should stop within ~0.5s of release; allow generous slack
    assert elapsed < 1.5, f"elapsed too long: {elapsed:.2f}s"
    assert out is not None
    print(f"  release_path:  OK  ({elapsed:.2f}s, terminate={proc.terminate_calls})")


def test_safety_cap_path():
    """Press but never release — should stop at the safety cap."""
    proc, elapsed, out = _run_one(safety_cap_secs=1.0,
                                  release_after=None,
                                  max_wait=3.0)
    assert proc.terminate_calls == 1, f"terminate calls: {proc.terminate_calls}"
    # Should be close to the 1.0s safety cap; allow slack
    assert 0.9 < elapsed < 2.5, f"elapsed out of range: {elapsed:.2f}s"
    print(f"  safety_cap:    OK  ({elapsed:.2f}s, terminate={proc.terminate_calls})")


def test_stop_while_waiting():
    """GUI stop while waiting for a press returns None without recording."""
    import voice_pipeline as vp

    stop = threading.Event()
    stop.set()
    with mock.patch.object(vp, "_start_arecord") as start:
        out = vp._record_ptt_gated(FakeHal(), status_q=None, max_secs=5, stop=stop)
    assert out is None, f"expected None, got {out!r}"
    assert not start.called, "arecord started despite stop"
    print("  stop_waiting:  OK")


def test_disconnect_while_waiting():
    """A dropped HAL link surfaces as ConnectionError so the loop can reconnect."""
    import voice_pipeline as vp

    hal = FakeHal()
    hal.state = lambda: {"ptt": 0, "connected": False}
    try:
        vp._record_ptt_gated(hal, status_q=None, max_secs=5)
    except ConnectionError:
        print("  disconnect:    OK")
        return
    raise AssertionError("no ConnectionError on disconnected HAL")


def test_hal_detects_transport_drop():
    """HalClient flips `connected` to False when its transport drops."""
    from overlay.pi5_hal.client import HalClient
    from overlay.pi5_hal.transport import MockTransport

    transport = MockTransport()
    hal = HalClient(transport)
    hal.connect(send_sync=False)
    assert hal.state()["connected"]
    transport.close()   # simulate the link dying underneath the client
    deadline = time.monotonic() + 2.0
    while hal.state()["connected"] and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not hal.state()["connected"], "HalClient still reports connected"
    hal.connect(send_sync=False)   # reconnect on the same client
    assert hal.state()["connected"], "reconnect failed"
    hal.disconnect()
    print("  hal_drop:      OK")


def test_led_tracking_id():
    """`led` keeps the LED number in `id`; its tracking id goes in `id_msg`."""
    import json
    from overlay.pi5_hal.client import HalClient
    from overlay.pi5_hal.transport import MockTransport

    transport = MockTransport()
    hal = HalClient(transport)
    hal.connect(send_sync=False)
    first = hal.set_led(7, on=True)
    second = hal.set_led(7, on=False)
    hal.disconnect()
    frames = [json.loads(line) for line in transport.sent]
    assert [f["id"] for f in frames] == [7, 7], frames
    assert [f["id_msg"] for f in frames] == [first, second] and first != second, frames
    print("  led_id_msg:    OK")


def main() -> int:
    print("PTT streaming-recording smoke test")
    try:
        test_release_path()
        test_safety_cap_path()
        test_stop_while_waiting()
        test_disconnect_while_waiting()
        test_hal_detects_transport_drop()
        test_led_tracking_id()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
