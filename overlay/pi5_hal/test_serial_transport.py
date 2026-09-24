"""Tests for the serial link to the RP2040 panel — no hardware needed.

Uses pyserial's ``loop://`` device (whatever is written comes straight back)
so the real SerialTransport + HalClient code runs end to end, including an
unplug and reconnect. Port auto-detection runs against faked USB listings.

Run::

    python -m overlay.pi5_hal.test_serial_transport

Standalone script like overlay/scenario/test_ptt_smoke.py: prints PASS or
exits non-zero. Needs pyserial (overlay/pi5_hal/requirements.txt).
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
import types
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from overlay.pi5_hal.client import HalClient  # noqa: E402
from overlay.pi5_hal import transport as tp  # noqa: E402


def _port(device, vid=None, interface=None, description="n/a"):
    return types.SimpleNamespace(device=device, vid=vid, interface=interface, description=description)


def test_open_transport_specs():
    assert isinstance(tp.open_transport("ws://127.0.0.1:8765/hal"), tp.WebsocketTransport)
    t = tp.open_transport("serial:auto")
    assert isinstance(t, tp.SerialTransport) and t.port == "auto" and t.baud == 115200
    t = tp.open_transport("serial:/dev/ttyACM1?baud=9600")
    assert (t.port, t.baud) == ("/dev/ttyACM1", 9600)
    assert tp.open_transport("/dev/ttyACM0").port == "/dev/ttyACM0"
    assert tp.open_transport("COM5").port == "COM5"
    assert tp.open_transport("serial:").port == "auto"
    try:
        tp.open_transport("http://nope")
    except ValueError:
        pass
    else:
        raise AssertionError("bad spec accepted")
    print("  specs:        OK")


def test_find_rp2040_port():
    listing = [
        _port("/dev/ttyAMA0"),                                       # Pi UART
        _port("/dev/ttyACM1", 0x2341, description="Nicla Voice"),    # Arduino
        _port("/dev/ttyACM0", 0x239A, "CircuitPython CDC control"),  # Metro console
    ]
    with mock.patch("serial.tools.list_ports.comports", return_value=listing):
        assert tp.find_rp2040_port() == "/dev/ttyACM0"
    # With the second (data) CDC channel enabled, prefer it over the REPL console
    listing.append(_port("/dev/ttyACM2", 0x239A, "CircuitPython CDC2 control"))
    with mock.patch("serial.tools.list_ports.comports", return_value=listing):
        assert tp.find_rp2040_port() == "/dev/ttyACM2"
    with mock.patch("serial.tools.list_ports.comports", return_value=listing[:2]):
        try:
            tp.find_rp2040_port()
        except RuntimeError as e:
            assert "no RP2040" in str(e) and "Nicla Voice" in str(e), e
        else:
            raise AssertionError("missing board not reported")
    print("  auto-detect:  OK")


def _wait(pred, secs=3.0):
    deadline = time.monotonic() + secs
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.05)
    return False


def test_loopback_events_unplug_reconnect():
    t = tp.SerialTransport("loop://")
    hal = HalClient(t)
    hal.connect(send_sync=False)
    assert hal.state()["connected"] and t.device == "loop://"

    # A frame the firmware would send (ptt press) arrives as an input event
    t.send(json.dumps({"t": "ptt", "state": 1, "ms": 1}))
    evt = hal.wait_for_event("ptt", timeout=3.0)
    assert evt is not None and hal.state()["ptt"] == 1, evt
    # Commands go out as one JSON line each; the loop device echoes them back
    echoed: list[dict] = []
    hal.on("led", echoed.append)
    msg_id = hal.set_led(3, on=True)
    assert _wait(lambda: echoed), "led command never went over the wire"
    assert echoed[0] == {"t": "led", "id": 3, "v": 255, "id_msg": msg_id}, echoed

    # Unplug: the port disappears under the reader
    t.ser.close()
    assert _wait(lambda: not hal.state()["connected"]), "unplug not detected"

    # Reconnect on the same client, like voice_pipeline's overlay loop does
    hal.disconnect()
    hal.connect(send_sync=False)
    assert hal.state()["connected"]
    t.send(json.dumps({"t": "key", "pos": "ARM", "ms": 2}))
    assert _wait(lambda: hal.state()["key"] == "ARM"), "no events after reconnect"
    hal.disconnect()
    print("  loopback:     OK")


def test_overlay_loop_waits_for_board():
    """voice_pipeline with serial:auto and no board plugged in: retries, doesn't crash."""
    sys.modules.setdefault("cv2", types.SimpleNamespace())
    import voice_pipeline as vp

    state = vp.make_default_state()
    q: queue.Queue = queue.Queue()
    with mock.patch.object(vp, "OVERLAY_HAL_URL", "serial:auto"), \
         mock.patch("serial.tools.list_ports.comports", return_value=[]):
        th = threading.Thread(target=vp._run_overlay_loop, args=(state, q, "space_command_launch"), daemon=True)
        th.start()
        time.sleep(1.0)
        state.stop.set()
        th.join(5.0)
    assert not th.is_alive(), "overlay loop did not stop"
    events = list(q.queue)
    assert any(k == "error" and "no RP2040" in text for k, text in events), events
    print("  no-board:     OK")


def main() -> int:
    print("serial transport tests")
    try:
        test_open_transport_specs()
        test_find_rp2040_port()
        test_loopback_events_unplug_reconnect()
        test_overlay_loop_waits_for_board()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
