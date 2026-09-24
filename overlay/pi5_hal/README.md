# pi5_hal — Pi 5 HAL client

Pi-side Python client for the overlay's JSON-lines hardware protocol.
Connects to either the **browser simulator** (WebSocket) or the **RP2040
firmware** (USB CDC serial) with the same API.

See `overlay/docs/HAL_PROTOCOL.md` for the wire format.

## Install

```bash
pip install -r overlay/pi5_hal/requirements.txt
```

`pyserial` is optional — only needed for `SerialTransport` once real
hardware is on the bench.

## Library usage

```python
from pi5_hal import HalClient, WebsocketTransport

hal = HalClient(WebsocketTransport("ws://127.0.0.1:8765/hal"))

# Subscribe before connecting if you want the boot greeting
hal.on("hello", lambda m: print("controller fw", m["fw"], "caps", m["caps"]))
hal.on("switch", lambda m: print(f"switch {m['id']} -> {m['state']}"))
hal.on("intent", lambda m: print(f"intent {m['key']!r} ({m['conf']:.2f})"))

with hal:                              # connect / disconnect via context mgr
    hal.set_led(1, on=True)
    hal.write_lcd(1, "ALT 12000 OK")
    hal.write_lcd(2, "FUEL 087%  ARM")
    hal.render_oled("MASTER", "status",
                    {"scenario": "TEST", "arm": "SAFE", "health": "OK"})
    hal.play_sfx(7)                    # COMMS chirp
    print(hal.state())                 # snapshot of inputs + caps
```

Threading model: the client runs one daemon RX thread that updates its
internal state mirror and dispatches callbacks. Commands are sent
synchronously from the caller's thread.

For one-shot waits:

```python
hal.on("ptt", lambda m: None)          # (optional) register interest
msg = hal.wait_for_event("ptt", timeout=5.0)
if msg and msg["state"] == 1:
    print("PTT pressed within 5s")
```

## CLI

`python -m pi5_hal --help`

```
  tap                stream every frame on the wire
  led <id> on|off    set a single LED (1–50)
  leds <hex>         bulk LED update (default format: hex_pairs)
  clear              all LEDs off, LCD cleared
  sfx <slot>         trigger a CH358 sound slot (1–10)
  lcd <1|2> <text>   write a line to the 1602 LCD
  oled <B|MASTER> <layout> '<json data>'   render OLED layout
  state              print HAL state snapshot
  reset              reset the controller
```

Default transport is `ws://127.0.0.1:8765/hal`. Pass `--serial COM5`
(Windows) or `--serial /dev/ttyACM0` (Linux) to use a real RP2040 over
USB CDC instead, or `--serial auto` to find it by USB vendor id
(Adafruit `0x239A` / Raspberry Pi `0x2E8A`).

## Using the real panel from the voice assistant

`voice_pipeline.py` picks its link from `MINI_AI_OVERLAY_HAL`:

| Value | Link |
|---|---|
| `ws://127.0.0.1:8765/hal` (default) | Browser simulator |
| `serial:auto` | RP2040 panel over USB, found by vendor id on every (re)connect |
| `serial:/dev/ttyACM0` (`?baud=N` optional) | A specific serial device |

```bash
MINI_AI_OVERLAY=true MINI_AI_OVERLAY_HAL=serial:auto ~/mini-ai/.venv/bin/python ~/mini-ai/mini_ai_panel.py
```

The Pi user needs the `dialout` group to open `/dev/ttyACM*`; setup phase 8
adds it (log out and back in once afterwards). Unplugging the board is
handled like a simulator restart: the loop reports it and reconnects when the
board is back, re-detecting its port.

`open_transport(spec)` builds the matching transport from any of these
strings; `find_rp2040_port()` does the auto-detection.

## Transports

| Class                | Use                                |
|----------------------|------------------------------------|
| `WebsocketTransport` | Browser simulator (default)        |
| `SerialTransport`    | Real RP2040 firmware (USB CDC); `port="auto"` detects it |
| `MockTransport`      | In-process testing — inject lines, capture sends |

Adding a transport: implement `connect / send(line) / recv_line(timeout) / close`
and a `connected` property (False once the link drops).

Tests: `python -m overlay.pi5_hal.test_serial_transport` runs the real
`SerialTransport` against pyserial's `loop://` device (events, commands,
unplug + reconnect) and auto-detection against faked USB listings.
