"""mini-ai overlay — RP2040 main loop.

Runs continuously after boot.py:
  1. drains incoming JSON-lines commands from Pi 5 (USB CDC)
  2. polls input peripherals; emits events when state changes
  3. emits a periodic heartbeat

The peripheral drivers in lib/peripherals.py start as stubs that no-op silently.
Replace each stub with a real driver as the corresponding hardware is wired.
The protocol layer is fully functional from day one — the simulator and the
Pi-side code can be developed against a stub-only firmware.

See overlay/docs/HAL_PROTOCOL.md for the wire format.
"""
import time


from lib.protocol import Protocol
from lib.peripherals import Peripherals
from config import CONFIG


FW_VERSION = "0.1.0"
HEARTBEAT_MS = 5000


def ms_now() -> int:
    return time.monotonic_ns() // 1_000_000


def handle_command(msg, peris, proto):
    t = msg.get("t")
    # `led` carries the LED number in `id`; its tracking id is `id_msg` (HAL_PROTOCOL §5.1)
    msg_id = msg.get("id_msg") if t == "led" else msg.get("id")
    try:
        if t == "led":
            peris.leds.set_one(msg["id"], msg.get("v", 255))
        elif t == "leds":
            peris.leds.set_bulk(msg.get("values", ""), msg.get("format", "hex_pairs"))
        elif t == "lcd":
            peris.lcd.write_line(msg.get("line", 1), msg.get("text", ""))
        elif t == "lcd_clear":
            peris.lcd.clear()
        elif t == "oled":
            peris.oled.render(msg.get("display", "B"), msg.get("layout", "text"),
                              msg.get("data", {}))
        elif t == "sfx":
            peris.sfx.trigger(msg["slot"], msg.get("pulse_ms", 100))
        elif t == "sfx_seq":
            peris.sfx.trigger_seq(msg["slot"], msg.get("count", 1),
                                  msg.get("interval_ms", 1000))
        elif t == "sync":
            peris.emit_sync(ms_now())
        elif t == "reset":
            peris.reset()
        else:
            _ack(proto, msg_id, False, f"unknown type {t!r}")
            return
        _ack(proto, msg_id, True)
    except Exception as exc:
        if msg_id is not None:
            _ack(proto, msg_id, False, str(exc))
        else:
            proto.send({"t": "err", "code": "CMD_FAIL",
                        "msg": "{}: {}".format(t, exc)})


def _ack(proto, msg_id, ok, err=None):
    if msg_id is None:
        return
    frame = {"t": "ack", "of": msg_id, "ok": ok}
    if err:
        frame["err"] = err
    proto.send(frame)


def main():
    proto = Protocol()
    peris = Peripherals(CONFIG, proto)

    proto.send({"t": "hello", "fw": FW_VERSION,
                "caps": peris.capabilities(),
                "ts": ms_now()})

    peris.self_test()
    proto.send({"t": "ready", "ms": ms_now()})

    last_hb = ms_now()
    while True:
        # 1) drain inbound commands
        for msg in proto.drain():
            handle_command(msg, peris, proto)

        # 2) poll inputs (may emit events)
        peris.poll(ms_now())

        # 3) heartbeat
        now = ms_now()
        if now - last_hb >= HEARTBEAT_MS:
            proto.send({"t": "heartbeat", "ms": now, "uptime_ms": now})
            last_hb = now

        # short yield to keep USB serial responsive
        time.sleep(0.001)


main()
