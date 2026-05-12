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
USB CDC instead.

## Transports

| Class                | Use                                |
|----------------------|------------------------------------|
| `WebsocketTransport` | Browser simulator (default)        |
| `SerialTransport`    | Real RP2040 firmware (USB CDC)     |
| `MockTransport`      | In-process testing — inject lines, capture sends |

Adding a transport: implement `connect / send(line) / recv_line(timeout) / close`.
