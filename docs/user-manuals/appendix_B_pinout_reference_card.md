<!-- Print: landscape, fit to 1 page. Designed to live next to the bench. -->

# Appendix B — Pinout Reference Card

This is the cheat-sheet for the build, designed to live next to your bench. Print one page, landscape, and keep it clipped to the back of your clipboard. Every wire, address, and command you'll touch in chapters 5–14 is on here. The chapter where each item is introduced is in parentheses — flip back to it if you need the full story.

## Metro RP2040 — pin map

The Metro is the panel's brain. Every wire that leaves a Metro pin is listed here. Wire colour follows the manual's convention (see Ch 4).

| Metro pin | Function                              | Wire colour | Goes to                            |
|-----------|---------------------------------------|-------------|------------------------------------|
| 3.3 V     | 3.3 V supply (board-generated)        | Orange      | Logic-level pull-ups, if used      |
| 5 V (VBUS)| 5 V in from USB-C                     | Red         | Breadboard +5 V rail (Ch 4)        |
| GND × n   | Ground (any of several GND pins)      | Black       | Breadboard GND rail (Ch 4)         |
| **GP4**   | I²C SDA (shared bus)                  | Yellow      | MCP23017, 1602 LCD, both OLEDs (Ch 7) |
| **GP5**   | I²C SCL (shared bus clock)            | Blue        | Same four I²C devices (Ch 7)       |
| **GP6**   | PTT button input *(direct GPIO option)* | Green     | PTT button — only if not routed via MCP (Ch 11) |
| **GP7**   | PIR motion input                      | Green       | HC-SR501 OUT pin (Ch 11)           |
| **GP10**  | 74HC595 **SER** (serial data in)      | Green       | Chip 1 pin 14 of the LED chain (Ch 10) |
| **GP11**  | 74HC595 **SRCLK** (shift clock)       | Green       | All 7 chips' pin 11 (shared) (Ch 10) |
| **GP12**  | 74HC595 **RCLK** (latch / store clock)| Green       | All 7 chips' pin 12 (shared) (Ch 10) |
| **GP13**  | 74HC595 **OE** (output enable, active low) | Green  | All 7 chips' pin 13 — tie to GND if not used (Ch 10) |
| **GP14**  | SFX slot 1 trigger (CH358 K1, ACK)    | Green       | Base of 2N3904 driver 1 (Ch 6)     |
| **GP15**  | SFX slot 2 trigger (CH358 K2, DENY)   | Green       | Base of 2N3904 driver 2 (Ch 6)     |
| **GP16**  | SFX slot 3 trigger (CH358 K3, CAUTION)| Green       | Base of 2N3904 driver 3 (Ch 6)     |
| **GP17**  | SFX slot 4 trigger (CH358 K4, ALARM)  | Green       | Base of 2N3904 driver 4 (Ch 6)     |
| **GP18**  | SFX slot 5 trigger (CH358 K5, ARM)    | Green       | Base of 2N3904 driver 5 (Ch 6)     |
| **GP19**  | SFX slot 6 trigger (CH358 K6, DISARM) | Green       | Base of 2N3904 driver 6 (Ch 6)     |
| **GP20**  | SFX slot 7 trigger (CH358 K7, COMMS)  | Green       | Base of 2N3904 driver 7 (Ch 6)     |
| **GP21**  | SFX slot 8 trigger (CH358 K8, CLICK)  | Green       | Base of 2N3904 driver 8 (Ch 6)     |
| **GP22**  | SFX slot 9 trigger (CH358 K9, TICK)   | Green       | Base of 2N3904 driver 9 (Ch 6)     |
| **GP26**  | SFX slot 10 trigger (CH358 K10, STATUS)| Green      | Base of 2N3904 driver 10 (Ch 6)    |

Source of truth: `overlay/firmware/rp2040/config.py`. If you change a pin there, change it here.

## MCP23017 — I²C I/O expander (address 0x20)

The MCP23017 expands the Metro's I²C bus into 16 GPIO lines. We use 12 of the 16 (Ch 9 + Ch 11). The other 4 are spare. Default I²C address is **0x20** with the three address pins (A0, A1, A2) all tied to GND.

| MCP pin | Bank label | Carries                  | Wired to                       |
|---------|------------|--------------------------|--------------------------------|
| 21      | **GPA0**   | Toggle switch **S1**     | Switch leg → GND (Ch 9)        |
| 22      | **GPA1**   | Toggle switch **S2**     | Switch leg → GND (Ch 9)        |
| 23      | **GPA2**   | Toggle switch **S3**     | Switch leg → GND (Ch 9)        |
| 24      | **GPA3**   | Toggle switch **S4**     | Switch leg → GND (Ch 9)        |
| 25      | **GPA4**   | Toggle switch **S5**     | Switch leg → GND (Ch 9)        |
| 26      | **GPA5**   | Toggle switch **S6**     | Switch leg → GND (Ch 9)        |
| 27      | **GPA6**   | Toggle switch **S7**     | Switch leg → GND (Ch 9)        |
| 28      | **GPA7**   | Toggle switch **S8**     | Switch leg → GND (Ch 9)        |
| 1       | **GPB0**   | Toggle switch **S9**     | Switch leg → GND (Ch 9)        |
| 2       | **GPB1**   | Toggle switch **S10**    | Switch leg → GND (Ch 9)        |
| 3       | **GPB2**   | MT-301 key **SAFE** contact | Key aux contact → GND (Ch 11) |
| 4       | **GPB3**   | MT-301 key **ARM** contact  | Key aux contact → GND (Ch 11) |
| 5–8     | GPB4–GPB7  | *spare*                  | leave unwired                  |

Other MCP23017 pins to know:

| MCP pin | Function    | Wired to                                |
|---------|-------------|-----------------------------------------|
| 9       | VDD (power) | +5 V rail (red)                          |
| 10      | VSS (GND)   | GND rail (black)                         |
| 11      | NC          | leave unconnected                       |
| 12      | SCL         | Metro GP5 (shared I²C, blue wire)        |
| 13      | SDA         | Metro GP4 (shared I²C, yellow wire)      |
| 14      | NC          | leave unconnected                       |
| 15      | A0          | GND  ⎤                                   |
| 16      | A1          | GND  ⎬ all three to GND → address `0x20`|
| 17      | A2          | GND  ⎦                                   |
| 18      | RESET       | +5 V rail (active low — tie high)        |
| 19–20   | INTB / INTA | leave unconnected (not used)            |

All switches are **active-low** with internal pull-ups enabled in firmware (Ch 9). Closed = pin reads 0.

## 74HC595 shift-register chain — 50 LEDs over 7 chips

Seven 74HC595 chips daisy-chained. Each chip drives 8 outputs (Q0–Q7). Chip 7 uses its Q0 only — the remaining 7 outputs of chip 7 are unused. Total = 50 LEDs. Bit order in `leds` commands: **LED 1 = chip 1 Q0**, LED 8 = chip 1 Q7, LED 9 = chip 2 Q0, … LED 50 = chip 7 Q1. The 3 highest bits of chip 7 are ignored.

| Chip # | LEDs driven | Role group (from `canonical/leds.yaml`)             |
|--------|-------------|-----------------------------------------------------|
| **1**  | LEDs 1–8    | switch mirrors S1–S8 (Ch 9, Ch 10)                  |
| **2**  | LEDs 9–16   | switch mirrors S9–S10 + sequence progress 11–16     |
| **3**  | LEDs 17–24  | sequence progress 17–20 + scenario status 21–24     |
| **4**  | LEDs 25–32  | scenario status 25–30 + alarm 31–32                 |
| **5**  | LEDs 33–40  | alarm annunciator                                   |
| **6**  | LEDs 41–48  | alarm annunciator                                   |
| **7**  | LEDs 49–50 *(Q0–Q1)*; Q2–Q7 unused | alarm annunciator (tail of cluster) |

**Daisy-chain wiring** (Ch 10): each chip's **Q7'** (pin 9, serial out) goes to the **SER** (pin 14) of the next chip. The control lines **SRCLK** (pin 11), **RCLK** (pin 12), and **OE** (pin 13) are shared — wire them in parallel across all 7 chips. The first chip's SER comes from Metro **GP10**.

> **TIP.** If a whole 8-LED block is dark, suspect that chip first. If a whole *half* of the chain is dark, suspect the SER wire between the last working chip and the first dark one — that's where the conga line broke.

## I²C address table

All four I²C devices share the same two wires: **SDA** (yellow, Metro GP4) and **SCL** (blue, Metro GP5). Each device has a unique 7-bit address so the Metro can talk to one at a time.

| Address | Device                          | Introduced in | Notes                                  |
|---------|----------------------------------|---------------|----------------------------------------|
| `0x20`  | **MCP23017** I/O expander        | Ch 9          | A0=A1=A2=GND. RESET tied high.         |
| `0x27`  | **1602 LCD** (PCF8574 backpack)  | Ch 7          | Some backpacks ship at `0x3F` — scan if it doesn't respond. |
| `0x3C`  | **OLED panel B** (SSD1306)       | Ch 8          | Default address — leave the jumper alone.|
| `0x3D`  | **OLED master** (STEMMA QT)      | Ch 8          | Move the **address jumper** to flip it from 0x3C → 0x3D so it doesn't collide with panel B. (Ch 8 details the solder bridge.) |

> **MISTAKE.** *(common error)* Both OLEDs ship at 0x3C. If you don't change one, both displays will fight on the bus and at least one of them won't render. Fix: change the address jumper on the **master** OLED. (Ch 8.)

## CH358 K-pin → SFX role mapping

The CH358D sound module plays one of 10 WAVs from a TF card. Each K-pin (K1..K10) triggers the corresponding slot. The role names below come from `overlay/canonical/sfx_bank.yaml`. WAVs are generated by `python overlay/tools/generate_sfx.py` (Ch 6).

| K-pin | Slot | Role     | What it sounds like                       | Triggered by                          |
|-------|------|----------|-------------------------------------------|---------------------------------------|
| **K1**| 1    | ACK      | Friendly short rising chirp               | Command acknowledged (Ch 6, Ch 14)    |
| **K2**| 2    | DENY     | Low descending buzz                       | Refused / arm-gated command           |
| **K3**| 3    | CAUTION  | Triple mid-pitch chirp                    | Yellow advisory                        |
| **K4**| 4    | ALARM    | Loud alternating klaxon                   | Critical / hull-breach / abort        |
| **K5**| 5    | ARM      | Mechanical clunk + tone                   | Key turned to ARM (Ch 11)             |
| **K6**| 6    | DISARM   | Softer descending mechanical              | Key turned to SAFE (Ch 11)            |
| **K7**| 7    | COMMS    | Squelch burst + clean chirp               | Mic going hot / LLM about to speak    |
| **K8**| 8    | CLICK    | Very short crisp tick                     | Any switch edge, PTT press (Ch 9)     |
| **K9**| 9    | TICK     | Single 1 kHz beep                         | Countdown step (use `sfx_seq`)        |
| **K10**| 10   | STATUS   | Four-note sweep (C-E-G-B)                 | Scenario change / boot complete       |

Each K-pin is driven by a **2N3904 NPN transistor** with a **4.7 kΩ base resistor** from the Metro GPIO (Ch 6). The K-pin is **active-low** — the transistor pulls it to GND for `pulse_ms` (default 100 ms).

## Quick CLI commands

Run these on the Pi 5. Each one is one line. Most are in `overlay/pi5_hal` — see Ch 6, Ch 7, Ch 10, and Ch 14 for context.

| Command | What it does | Chapter |
|---------|--------------|---------|
| `python -m overlay.pi5_hal sfx 1`              | Play SFX slot 1 (ACK chime). | Ch 6 |
| `python -m overlay.pi5_hal sfx 4 --pulse-ms 200` | Play slot 4 (ALARM) with a longer trigger pulse. | Ch 6 |
| `python -m overlay.pi5_hal lcd 1 "HELLO WORLD"` | Write line 1 of the 1602 LCD. | Ch 7 |
| `python -m overlay.pi5_hal lcd-clear`           | Blank the LCD. | Ch 7 |
| `python -m overlay.pi5_hal oled b alert --title BREACH --subtitle "hull section 3"` | Render an alert on OLED panel B. | Ch 8 |
| `python -m overlay.pi5_hal oled master status --scenario "Test Console" --arm SAFE` | Render the master status block. | Ch 8 |
| `python -m overlay.pi5_hal led 17 255`          | Light a single LED (LED 17, full on). | Ch 10 |
| `python -m overlay.pi5_hal leds FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00` | Bulk-set all 50 LEDs in one frame (hex pairs). | Ch 10 |
| `python -m overlay.pi5_hal sync`                | Ask the controller to dump its full current state. | Ch 14 |
| `python -m overlay.pi5_hal reset`               | Soft-reset the controller (re-emits `hello` and `ready`). | Ch 5 |
| `python -m overlay.scenario.demo --repl`        | Start the full voice loop (mic → AI → panel + voice). | Ch 14 |

**Serial terminal** (Ch 5): the Metro is on a USB-CDC port at **115200 baud, 8N1, no flow control**. Use **PuTTY** on Windows, **`screen /dev/tty.usbmodem* 115200`** on macOS, or **`screen /dev/ttyACM0 115200`** on Linux. Watch for `{"t":"hello",...}` and `{"t":"ready",...}` at boot.

> **CHECKPOINT.** If `python -m overlay.pi5_hal sfx 1` produces a chime, your CH358 wiring is good (Ch 6). If `lcd 1 "HELLO WORLD"` shows text, your I²C bus is good (Ch 7). If both work, you can confidently move on to Ch 8.

---

*Source files behind this card: `overlay/firmware/rp2040/config.py` (Metro pins), `overlay/canonical/switches.yaml` (MCP channels), `overlay/canonical/leds.yaml` (LED groups), `overlay/canonical/sfx_bank.yaml` (K-pin roles), `overlay/canonical/hardware_modules.yaml` (I²C addresses), `overlay/docs/HAL_PROTOCOL.md` (CLI commands).*
