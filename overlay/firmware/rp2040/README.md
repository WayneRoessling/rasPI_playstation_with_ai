# RP2040 firmware — mini-ai overlay

CircuitPython firmware for the **Adafruit Metro RP2040** that bridges
the Pi 5 to the physical control panel hardware.

## Files

| File                      | Purpose                                    |
|---------------------------|--------------------------------------------|
| `boot.py`                 | Runs once at startup; disables auto-reload |
| `code.py`                 | Main loop: command dispatch + poll + heartbeat |
| `config.py`               | Pin assignments + per-peripheral `enabled` flags |
| `lib/protocol.py`         | Non-blocking JSON-lines over USB CDC       |
| `lib/peripherals.py`      | One stub class per peripheral — replace incrementally |

## Flashing & deploying

1. Install **CircuitPython 9.x** for the Metro RP2040
   ([download](https://circuitpython.org/board/adafruit_metro_rp2040/)).
   Hold BOOTSEL while plugging USB → drag the `.uf2` onto the `RPI-RP2`
   drive.

2. The board re-enumerates as a `CIRCUITPY` USB drive. Copy these files
   onto it preserving the layout:
   ```
   CIRCUITPY/
   ├── boot.py
   ├── code.py
   ├── config.py
   └── lib/
       ├── __init__.py
       ├── protocol.py
       ├── peripherals.py
       └── (Adafruit driver libraries from the CircuitPython bundle)
   ```

3. Download the matching CircuitPython library bundle, copy these driver
   folders into `CIRCUITPY/lib/`:
   - `adafruit_bus_device`
   - `adafruit_mcp230xx` (10 toggle switches + key contacts)
   - `adafruit_character_lcd` (1602 LCD)
   - `adafruit_ssd1306` (both OLEDs)
   - `adafruit_framebuf` (OLED layouts)
   - `adafruit_74hc595` (LED chain)

4. Connect a serial terminal to the Metro's USB CDC at **115200 baud**
   (it appears as `/dev/ttyACM0` on Linux, `COMn` on Windows). Reset the
   board — you should see `{"t":"hello","fw":"0.1.0", ...}` followed by
   `{"t":"ready", ...}`.

## Bringing up peripherals

The firmware advertises a `caps` list in its hello frame based on the
`enabled` flag for each peripheral in `config.py`. **All peripherals
start disabled.** Bring them up one at a time:

1. Wire the hardware.
2. Set `enabled: True` in the relevant section of `config.py`.
3. Replace the corresponding stub body in `lib/peripherals.py` with the
   real driver code (the docstring on each class lists the Adafruit
   library to use).
4. Save → re-enter REPL → `import supervisor; supervisor.reload()`.
5. Verify the new capability appears in `hello.caps` and the device
   behaves correctly via the simulator's protocol log or a quick
   manual frame from the Pi side:
   ```
   {"t":"sfx","slot":1,"pulse_ms":100,"id":1}
   ```

## Capability list

```
switches  10 toggle switches (MCP23017 I2C expander @ 0x20)
ptt       PTT momentary button (direct GPIO)
pir       Inland PIR motion sensor (direct GPIO)
key       MT-301R4P-P rotary isolator (2 contacts via MCP23017)
leds      50 LEDs via 74HC595 chain (7 chips, binary on/off)
lcd       1602 character LCD (PCF8574 I2C backpack @ 0x27)
oled      2× SSD1306 OLED 128×64 (@ 0x3C panel B, @ 0x3D master)
sfx       CH358D-TF-1G sound module (10 K-pins via 2N3904 NPN drivers)
```

## Wiring notes

- **Shared I2C bus**: SDA=GP4, SCL=GP5 at 400 kHz. All four I2C devices
  (MCP23017, 1602 LCD, 2× OLED) hang off this bus. Add 4.7 kΩ pull-ups
  if not already provided by a breakout board.
- **74HC595 chain**: 7 chips daisy-chained, total 56 outputs (we use the
  first 50). Each LED needs its own current-limit resistor
  (≈330 Ω for 5 mA at 3.3 V).
- **CH358 trigger drivers**: 10 × 2N3904 NPN transistors. RP2040 GPIO
  → 4.7 kΩ base resistor → base. Emitter → GND. Collector → CH358 K-pin.
  K-pins float at the CH358's internal pull-up voltage when idle; the
  transistor pulls them to GND for `pulse_ms` to trigger.
- **MT-301R4P-P**: use **auxiliary contacts only at logic voltage**.
  Do not switch mains through this. Wire one pole to indicate SAFE,
  one to indicate ARM, into MCP23017 inputs with pull-ups.

## Debugging

- The REPL is the same CDC channel as the protocol. Stop the running
  code with Ctrl-C, then drive peripherals interactively:
  ```python
  >>> from lib.peripherals import Peripherals
  >>> from lib.protocol import Protocol
  >>> from config import CONFIG
  >>> p = Peripherals(CONFIG, Protocol())
  >>> p.leds.set_one(1, 255)
  ```
- For a clean separation, enable `usb_cdc.data` in `boot.py` (see
  comment there) and update `lib/protocol.py` to use it.
