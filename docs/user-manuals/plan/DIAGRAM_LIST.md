# Diagram & Photograph List

Every illustration the manual needs, organized by chapter. Each entry
has:

- **ID** — `D-<chapter>.<n>` (matches the reference IDs in
  [`BUILD_MANUAL_PLAN.md`](BUILD_MANUAL_PLAN.md))
- **Kind** — diagram (drawn/Fritzing/vector), photograph, or screenshot
- **What it shows**
- **Status** — `TODO` until produced

Recommended sources:
- **Diagrams** → Fritzing for breadboard views; Inkscape for clean
  vector pinouts and analogies.
- **Photographs** → taken at the bench during the real build, on a
  cutting-mat background, in bright even light.
- **Screenshots** → captured directly from the simulator browser tab,
  the terminal, or the file explorer.

---

## Chapter 00 — Welcome & Safety

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-0.1 | Photo       | Tool tray: USB-C cable, USB-A cable, side cutters, wire strippers, screwdriver, jumper-wire kit, breadboard, phone-for-photos. Labels overlaid. | TODO |
| D-0.2 | Photo       | The finished panel (small, teaser shot) — "this is what you'll have built." | TODO |

## Chapter 01 — What You Already Have (Mini-AI Pi 5)

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-1.1 | Photo       | Annotated photo of every existing Pi 5 build component arranged on a tray: Pi 5, PSU, Yahboom mic/spkr, C920, SSD. | TODO |
| D-1.2 | Photo       | Close-up of the official 27 W USB-C PSU label, emphasising the "27 W" rating. | TODO |

## Chapter 02 — Big Picture of the Control Panel

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-2.1 | Diagram     | The four-box architecture: Pi 5 ↔ Metro RP2040 (panel brain) + Nicla (ear), Metro ↔ Panel (switches/LEDs/displays/sound/key). | TODO |
| D-2.2 | Screenshot  | The browser simulator UI running on localhost:8765, showing switches/LEDs/OLED/LCD/SFX/PTT/PIR/key sections. | TODO |

## Chapter 03 — Setting Up Your Workspace

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-3.1 | Diagram     | Breadboard internal-connection illustration: how the 5 holes in each column are joined, and how the + and - rails run the full length. | TODO |
| D-3.2 | Photo       | An organized workspace: breadboard centered, jumper-wire kit fan-shaped to the left, parts trays to the right, phone propped to the side. | TODO |

## Chapter 04 — Powering Things

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-4.1 | Diagram     | The Pi 5 40-pin GPIO header with **5 V** pins (2, 4) and **GND** pins (6, 9, 14, 20, 25, 30, 34, 39) highlighted in red and black. | TODO |
| D-4.2 | Diagram     | Two female-to-male jumpers running from Pi 5 pins 2 and 6 to the breadboard's red (+) and black (−) rails. | TODO |
| D-4.3 | Diagram     | The voltage = water-pressure analogy: a tank, a pipe with a narrow section, a flow gauge. Labels match the manual's analogy in §2 of `STYLE_GUIDE.md`. | TODO |

## Chapter 05 — First Test — the Metro RP2040 Alone

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-5.1 | Photo       | Metro RP2040 with the **BOOTSEL** button circled. | TODO |
| D-5.2 | Screenshot  | File-explorer view of the `RPI-RP2` USB drive with the CircuitPython `.uf2` being dragged onto it. | TODO |
| D-5.3 | Screenshot  | A serial terminal at 115200 baud showing `{"t":"hello",...}` and `{"t":"ready",...}` frames. | TODO |
| D-5.4 | Screenshot  | The `CIRCUITPY` drive in the OS file explorer with `boot.py`, `code.py`, `config.py`, and `lib/` visible. | TODO |

## Chapter 06 — The Sound Module (CH358D)

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-6.1 | Photo       | The CH358D-TF-1G module with K1–K10, VCC, GND, the speaker output, micro-USB, and TF-card slot all labelled. | TODO |
| D-6.2 | Diagram     | 2N3904 transistor pinout (flat side facing you): Emitter | Base | Collector. | TODO |
| D-6.3 | Diagram     | Breadboard wiring for one K-pin: Metro GPIO → 4.7 kΩ → 2N3904 base, emitter → GND rail, collector → CH358 K-pin. | TODO |
| D-6.4 | Photo       | Photo of D-6.3 actually wired on a breadboard. | TODO |
| D-6.5 | Photo       | All 10 K-pin drivers wired and labelled. | TODO |
| D-6.6 | Screenshot  | The TF card mounted on the computer with the 10 generated WAV files visible (`01.wav` through `10.wav`). | TODO |

## Chapter 07 — Panel Display A — the 1602 LCD

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-7.1 | Photo       | The 1602 LCD with I²C backpack, pins labelled VCC / GND / SDA / SCL. | TODO |
| D-7.2 | Diagram     | 4-wire wiring: LCD → breadboard rails + RP2040 GP4 (SDA) / GP5 (SCL). | TODO |
| D-7.3 | Photo       | The LCD showing `HELLO WORLD` after the CLI test. | TODO |
| D-7.4 | Photo       | Optional: address jumper or backpack pot adjustment (contrast). | TODO |

## Chapter 08 — Panel Display B + Master — Two OLEDs

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-8.1 | Photo       | OLED back side with the address-jumper pads or solder bridge circled and labelled. | TODO |
| D-8.2 | Diagram     | Both OLEDs hanging off the same I²C bus, sharing SDA/SCL with the 1602 LCD, addresses 0x3C and 0x3D. | TODO |
| D-8.3 | Photo       | Both OLEDs displaying different content (status block on master, alert on B). | TODO |

## Chapter 09 — Toggle Switches & MCP23017

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-9.1 | Diagram     | MCP23017 DIP-28 pinout with named columns: address pins (A0–A2), reset, I²C (SDA/SCL), GPA0–GPA7, GPB0–GPB7, interrupts, power. | TODO |
| D-9.2 | Diagram     | MCP23017 mounted across the breadboard center groove with power, reset, and I²C wired. | TODO |
| D-9.3 | Diagram     | One toggle switch wired: one leg to a GPA pin, other to GND rail. | TODO |
| D-9.4 | Photo       | All 10 switches wired and labelled S1–S10. | TODO |

## Chapter 10 — LEDs & the 74HC595 Chain

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-10.1 | Diagram    | 74HC595 DIP-16 pinout with labelled functions (SER/DS, OE, RCLK/ST_CP, SRCLK/SH_CP, MR, Q0–Q7, Q7'). | TODO |
| D-10.2 | Diagram    | One 74HC595 wired: power, GND, OE→GND, MR→VCC, control lines to Metro GPIOs, Q0–Q7 to 8 LEDs with current-limit resistors. | TODO |
| D-10.3 | Diagram    | Chain principle: Q7' of chip N → SER of chip N+1, control lines shared, daisy-chained. | TODO |
| D-10.4 | Diagram    | LED polarity: long leg = anode (+), short leg = cathode (−), flat side of plastic case = cathode. | TODO |
| D-10.5 | Photo      | Final 50-LED bank populated and lit in a test pattern. | TODO |

## Chapter 11 — PTT, PIR, MT-301 Key Switch

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-11.1 | Diagram    | PTT button wiring: one terminal → MCP pin, other → GND. | TODO |
| D-11.2 | Diagram    | Inland PIR pinout (VCC / GND / OUT) and trim-pots (sensitivity, hold-time). | TODO |
| D-11.3 | Diagram    | MT-301R4P-P contact layout with **only two** auxiliary poles in use, **at low voltage**, going to MCP inputs. Explicit "DO NOT WIRE TO MAINS" callout. | TODO |
| D-11.4 | Photo      | All three inputs wired and the panel showing a `key` event in the simulator log on key turn. | TODO |

## Chapter 12 — The Always-On Ear — Arduino Nicla Voice

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-12.1 | Photo      | Arduino Nicla Voice with USB-C port, microphone, IMU, and LED labelled. | TODO |
| D-12.2 | Photo      | Nicla plugged into the Pi 5 via USB. | TODO |
| D-12.3 | Screenshot | Pi 5 terminal showing a `wake` event log after saying the wake word. | TODO |

## Chapter 13 — Mounting Onto a Panel

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-13.1 | Diagram    | Single-page printable panel layout template: positions for 10 toggle switches, PTT, PIR window, 50 LEDs, both OLEDs, the LCD, the MT-301 key. With dimensions. | TODO |
| D-13.2 | Photo gallery | 2–3 example finished panels in different aesthetics (lab rig, sci-fi cosplay, museum exhibit). | TODO |

## Chapter 14 — First Real Run

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-14.1 | Photo      | Complete wired panel + Pi 5, USB cables, mic, speaker — the whole setup. | TODO |
| D-14.2 | Screenshot | Terminal output of `python -m overlay.scenario.demo --repl` in mid-conversation. | TODO |

## Chapter 15 — Troubleshooting

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-15.1 | Photo      | Multimeter set to DC volts, probes touching the breadboard 5 V rail (red probe) and GND rail (black probe), reading ~5.0 V. | TODO |
| D-15.2 | Screenshot | Simulator protocol log with annotations showing how to interpret the messages and find a problem. | TODO |

## Appendix B — Pinout Reference Card

| ID | Kind | What it shows | Status |
|---|---|---|---|
| D-B.1 | Diagram (printable) | One-page summary: Metro RP2040 pin map, MCP23017 connections, 74HC595 chain, I²C address table, CH358 K-pin → SFX role table. Designed for the back of a clipboard. | TODO |

---

## Summary

- **39 illustrations total** across the manual (32 chapter-specific +
  the appendix card; the master plan estimated ≈ 40, this list is the
  authoritative count).
- **18 are photographs** (taken at the bench during the real build).
- **17 are diagrams** (Fritzing breadboard views + Inkscape pinouts +
  the architecture and analogies).
- **6 are screenshots** (file explorer, terminal, simulator).

**Production order:**

1. **Diagrams first** for chapters 0–4 (independent of the bench).
2. **Photographs as the bench build happens**, in chapter order.
3. **Screenshots last**, after the firmware and simulator are running
   on the final hardware.

**Tools required:**

- Fritzing (free) — breadboard views.
- Inkscape (free) — pinout charts and the architecture diagram.
- Any phone camera with a macro mode — photos.
- The OS's built-in screenshot tool — screenshots.

Store all source files (`.fzz`, `.svg`, raw photos) under
`docs/user-manuals/source/` so they're version-controlled alongside the
rendered chapters. Final rendered images go under
`docs/user-manuals/images/`.
