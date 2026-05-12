"""Small CLI for ad-hoc HAL interaction.

Examples:
    # Watch every frame on the wire
    python -m pi5_hal --sim ws://127.0.0.1:8765/hal tap

    # Single commands
    python -m pi5_hal led 5 on
    python -m pi5_hal led 5 off
    python -m pi5_hal sfx 4
    python -m pi5_hal lcd 1 "ALT 12000 OK"
    python -m pi5_hal oled MASTER status '{"scenario":"TEST","arm":"SAFE","health":"OK"}'
    python -m pi5_hal state

The default transport is the simulator at ws://127.0.0.1:8765/hal.
Pass --serial PORT to talk to a real RP2040 over USB CDC.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from .client import HalClient
from .transport import WebsocketTransport, SerialTransport


def _transport(args):
    if args.serial:
        return SerialTransport(args.serial, args.baud)
    return WebsocketTransport(args.sim)


def cmd_tap(args):
    hal = HalClient(_transport(args))
    hal.on("*", lambda m: print(json.dumps(m)))
    hal.connect(send_sync=False)
    print(f"[tap] connected to {args.serial or args.sim}", file=sys.stderr)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        hal.disconnect()


def cmd_led(args):
    with HalClient(_transport(args)) as hal:
        on = args.state.lower() in ("on", "1", "true", "yes")
        mid = hal.set_led(args.id, on)
        print(f"[led] {args.id} -> {'on' if on else 'off'} (id={mid})")
        time.sleep(0.2)


def cmd_leds(args):
    with HalClient(_transport(args)) as hal:
        mid = hal.set_leds(args.values, args.format)
        print(f"[leds] format={args.format} (id={mid})")
        time.sleep(0.3)


def cmd_clear(args):
    with HalClient(_transport(args)) as hal:
        hal.clear_leds()
        hal.clear_lcd()
        print("[clear] LEDs off, LCD cleared")
        time.sleep(0.2)


def cmd_sfx(args):
    with HalClient(_transport(args)) as hal:
        mid = hal.play_sfx(args.slot, args.pulse_ms)
        print(f"[sfx] slot {args.slot} (id={mid})")
        time.sleep(0.4)


def cmd_lcd(args):
    with HalClient(_transport(args)) as hal:
        mid = hal.write_lcd(args.line, args.text)
        print(f"[lcd] line {args.line}: {args.text!r} (id={mid})")
        time.sleep(0.2)


def cmd_oled(args):
    with HalClient(_transport(args)) as hal:
        try:
            data = json.loads(args.data)
        except ValueError as e:
            print(f"error: data must be JSON: {e}", file=sys.stderr)
            sys.exit(2)
        mid = hal.render_oled(args.display, args.layout, data)
        print(f"[oled] {args.display} {args.layout} (id={mid})")
        time.sleep(0.2)


def cmd_state(args):
    with HalClient(_transport(args)) as hal:
        time.sleep(0.5)  # let sync round-trip
        print(json.dumps(hal.state(), indent=2))


def cmd_reset(args):
    with HalClient(_transport(args)) as hal:
        hal.reset()
        print("[reset] sent")
        time.sleep(0.2)


def build_parser():
    p = argparse.ArgumentParser(prog="pi5_hal", description=__doc__.splitlines()[0])
    p.add_argument("--sim", default="ws://127.0.0.1:8765/hal",
                   help="WebSocket URL of the simulator (default: %(default)s)")
    p.add_argument("--serial", metavar="PORT",
                   help="Serial port of the RP2040 (overrides --sim)")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("tap", help="stream every frame on the wire")
    s.set_defaults(func=cmd_tap)

    s = sub.add_parser("led", help="set a single LED")
    s.add_argument("id", type=int)
    s.add_argument("state", help="on | off")
    s.set_defaults(func=cmd_led)

    s = sub.add_parser("leds", help="bulk LED update")
    s.add_argument("values")
    s.add_argument("--format", default="hex_pairs", choices=["hex_pairs", "mask"])
    s.set_defaults(func=cmd_leds)

    s = sub.add_parser("clear", help="all LEDs off, LCD cleared")
    s.set_defaults(func=cmd_clear)

    s = sub.add_parser("sfx", help="trigger a CH358 sound slot")
    s.add_argument("slot", type=int, choices=range(1, 11))
    s.add_argument("--pulse-ms", type=int, default=100)
    s.set_defaults(func=cmd_sfx)

    s = sub.add_parser("lcd", help="write a line to the 1602 LCD")
    s.add_argument("line", type=int, choices=[1, 2])
    s.add_argument("text")
    s.set_defaults(func=cmd_lcd)

    s = sub.add_parser("oled", help="render OLED layout")
    s.add_argument("display", choices=["B", "MASTER"])
    s.add_argument("layout", choices=["text", "alert", "status", "icon", "raw"])
    s.add_argument("data", help='JSON, e.g. \'{"title":"BREACH"}\'')
    s.set_defaults(func=cmd_oled)

    s = sub.add_parser("state", help="print HAL state snapshot")
    s.set_defaults(func=cmd_state)

    s = sub.add_parser("reset", help="reset the controller")
    s.set_defaults(func=cmd_reset)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
    )
    args.func(args)


if __name__ == "__main__":
    main()
