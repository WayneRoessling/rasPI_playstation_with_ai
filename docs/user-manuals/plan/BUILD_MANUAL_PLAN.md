# Build Manual — Plan

The mini-ai hardware build manual is a step-by-step guide aimed at a
high-school-aged builder. This document is the **plan** for that manual —
what it covers, who it's for, how it reads, and the chapter-by-chapter
outline. The actual manual chapters will be written separately, against
this plan.

---

## 1. Reader profile

**Who the manual is written for:**
- Roughly 14–18 years old, comfortable with a computer (knows what a USB
  port is, can drag files between folders, can open a terminal when shown).
- Has *never* built electronics before.
- Has *never* soldered before.
- Has *never* used a breadboard before.

**What we assume the reader knows:**
- How to plug in a USB cable.
- How to follow a numbered checklist.
- How to copy a file from one folder to another.

**What we do NOT assume:**
- Any knowledge of voltage, current, resistors, transistors, GPIO, I²C,
  serial protocols, GND, pull-up resistors, or "active low."
- Any prior coding in Python, C, or CircuitPython.
- Any prior use of git, the command line beyond `cd` and running a script.

Every technical term is introduced **with its definition** the first time
it appears. The first introduction of any term uses **bold** + a plain-English
explanation. See [`STYLE_GUIDE.md`](STYLE_GUIDE.md).

---

## 2. Goal of the manual

After reading the manual cover-to-cover (and following along with the
physical hardware in front of them), the builder will have:

1. Identified every part in the existing mini-ai-pi build and the new
   control-panel parts.
2. Set up a safe workspace.
3. Connected, one module at a time, all of: the **Adafruit Metro RP2040**
   control board, the **CH358D-TF-1G** sound module, the **1602 LCD**, two
   **128×64 OLED** displays, the **MCP23017** I/O expander driving 10 toggle
   switches and the **MT-301R4P-P** key switch, the **74HC595** shift-register
   chain driving 50 LEDs, the **PTT** button, the **Inland PIR** motion
   sensor, and the **Arduino Nicla Voice** wake-word board.
4. Tested each module *as it was added* using the in-browser simulator
   and the `pi5_hal` CLI.
5. Run a full end-to-end demo: spoken command on the mic, the AI replies
   through the speaker and drives the panel.

If the builder gets stuck, the troubleshooting chapter tells them the
five most likely causes for each symptom and how to fix them.

---

## 3. Structure: one manual, multiple chapters

The manual is **one document delivered as a series of markdown files**
named `00_*.md` through `15_*.md` plus appendices. A reader follows
them in order. Each chapter is 15–30 minutes of reading + doing — short
enough that a builder can finish one in a single sitting and feel
progress.

The reader's path through the manual maps to *physical* progress on the
panel — Chapter 6 ends with audible sound, Chapter 7 ends with text on
a display, Chapter 10 ends with lit LEDs. **Visible wins land early and
often**, because losing motivation is the #1 reason people abandon
electronics builds.

### Chapter list

| # | Chapter | Outcome the reader achieves |
|---|---|---|
| 00 | **Welcome & Safety**                        | Reader knows what they're building, has the tools, and understands the four safety rules. |
| 01 | **What You Already Have — the Mini-AI Pi 5** | Reader has identified every part of the existing mini-ai build. |
| 02 | **The Big Picture of the Control Panel**    | Reader can draw, on paper, the four "boxes" of the new build and how they connect. |
| 03 | **Setting Up Your Workspace**               | Workspace is laid out, breadboard is mounted, ESD precautions explained. |
| 04 | **Powering Things**                         | 5V and GND rails wired from the Pi 5 to the breadboard; reader understands voltage / ground / share-a-ground. |
| 05 | **First Test — the Metro RP2040 Alone**     | RP2040 flashed with CircuitPython + overlay firmware; serial terminal shows the `hello` and `ready` frames. **First win.** |
| 06 | **The Sound Module (CH358D)**               | 10 SFX WAVs loaded onto the TF card; one transistor wired; firing slot 1 from the CLI produces an audible chirp. **Second win.** |
| 07 | **Panel Display A — the 1602 LCD**          | "HELLO WORLD" appears on the LCD from a CLI command. **Third win.** |
| 08 | **Panel Display B + Master — Two OLEDs**    | Both OLEDs render. Address-jumper trick is understood. |
| 09 | **Toggle Switches & the MCP23017**          | All 10 switches debounce and emit `switch` events visible in the simulator browser. |
| 10 | **LEDs & the 74HC595 Shift-Register Chain** | All 50 LEDs are individually addressable from the CLI. |
| 11 | **PTT, PIR, and the MT-301 Key Switch**     | Pressing PTT, walking past PIR, and turning the key all emit events. |
| 12 | **The Always-On Ear — Arduino Nicla Voice** | Saying "computer" on the mic triggers a `wake` event on the Pi 5. |
| 13 | **Mounting Everything Onto a Real Panel**   | Optional: panel cut/drilled, parts mounted with labels. |
| 14 | **First Real Run**                          | Reader runs the full voice-loop demo end-to-end. **Final win.** |
| 15 | **Troubleshooting**                         | Reader can look up symptoms → causes → fixes. |
| A | **Bill of Materials**                        | One-stop parts list with links and approximate costs. |
| B | **Pinout Reference Card**                    | Printable single-page cheat sheet. |
| C | **Glossary**                                 | A-to-Z of every term defined in the manual. |
| D | **Going Further**                            | "Where to next" — write a scenario, train Nicla, move to soldered protoboard. |

### Section-by-section detail

The detailed outline for each chapter — the questions it answers, the
checkpoints the reader must hit before moving on, and the diagrams it
needs — is at the bottom of this document
([§9 Chapter outlines](#9-chapter-outlines)).

---

## 4. Style at a glance

Full rules in [`STYLE_GUIDE.md`](STYLE_GUIDE.md). Highlights:

- **Conversational tone.** "We're going to plug this in here," not "The
  reader will insert the connector into the receptacle."
- **Every step is numbered.** Build steps live in `1. 2. 3. …` lists.
- **No jargon without a definition on first use.** "Now wire the
  **resistor** (a small component that limits how much electricity can
  flow, like a narrow part in a hose)…"
- **Visible callout boxes** for safety, tips, checkpoints, and optional
  deep-dives:
  > **WARNING.** The MT-301 key switch can be wired to mains voltage in
  > industrial use. **We will only use its low-voltage auxiliary contacts.**
  > Never connect this switch to household power.
- **Every wiring step has a diagram and a photo.** No exceptions.
- **Every chapter has a checkpoint.** "Before continuing to Chapter 7,
  you should hear the chime when you run `python -m overlay.pi5_hal sfx 1`."
- **First-win-fast.** Reader sees, hears, or feels success by the end of
  Chapter 5.

---

## 5. Build sequence — and why it's in this order

The order isn't arbitrary. Each module was chosen as the next one to wire
because:

1. **Metro RP2040 first.** Even with nothing else wired, the firmware
   emits `hello`/`ready` over USB. That proves the toolchain works — the
   reader hasn't soldered or wired anything yet and they've already had a
   "it speaks!" moment.
2. **Sound module second.** Audible feedback is the most motivating.
   Wiring is small (one transistor + two resistors for one slot —
   reader doesn't need all 10 to verify the principle). And no I²C bus
   conflict to debug.
3. **1602 LCD third.** First I²C device. Easy address, easy library,
   easy "HELLO WORLD" moment.
4. **OLEDs fourth.** Same I²C bus as the LCD. Introduces the
   address-jumper concept on the SECOND OLED (because the two of them
   ship at the same default address — common gotcha turned into a
   teachable moment).
5. **Switches fifth.** First *input* device. Introduces the MCP23017
   I²C expander, pull-ups, debouncing.
6. **LEDs sixth.** Most wiring of any module — saved for after the
   reader is comfortable with the breadboard. Introduces shift registers.
7. **PTT/PIR/Key seventh.** Reuses the same I²C expander pattern
   from chapter 9. Introduces the arm-gate safety pattern.
8. **Nicla last.** Standalone USB device; only wires up after
   everything else is working so wake-word events have somewhere to land.

If a builder gets to Chapter 5 and decides not to continue, they still
have a working "first test" they can show someone. If they only get
through Chapter 7, they have an LCD they can write text to. Every
stopping point is a usable result.

---

## 6. What this manual will NOT cover

Out of scope. Stated explicitly so future authors don't drift.

- **Soldering.** The reference build uses breadboards and jumper wires.
  Appendix D points the reader at where to learn soldering separately.
- **PCB design or fabrication.**
- **Custom enclosure design beyond a flat panel template.**
- **The mini-ai software stack (Whisper, Ollama, Piper) setup from
  scratch.** That's covered by the existing `setup_all.py` flow and the
  Pi-side project docs. The manual references those and trusts they ran.
- **Mains electrical wiring.** Every component in the bill of materials
  is powered from USB or breadboard-level voltages (≤5 V DC).
- **Training a custom Nicla wake-word model.** A pointer to Edge Impulse
  is in Appendix D for the curious; Chapter 12 uses a pre-trained model.
- **Driving the Arduino GIGA Display Shield.** Deferred until an
  Arduino GIGA R1 host board is procured (see Bill of Materials).
- **Operating system installation on the Pi 5.** The Pi is assumed to be
  already running per the existing mini-ai-pi setup automation.

---

## 7. Diagrams and photos

Every wiring step needs both a **diagram** (schematic-style or
Fritzing-style breadboard layout) and a **photograph** (so the reader
can compare what their bench looks like to the reference). The full
list is in [`DIAGRAM_LIST.md`](DIAGRAM_LIST.md) — approximately 40
illustrations total.

Open question: how are these produced?

| Option | Pro | Con |
|---|---|---|
| Fritzing (free)            | Industry-standard breadboard look | Has a learning curve; some parts not in library |
| Hand-drawn + scanned        | Friendly, approachable | Not reproducible without the original artist |
| Inkscape / vector by hand   | Polished | Slowest to produce |
| Photographs only            | Real | Hard to label, less clear at small sizes |

Recommendation: **Fritzing for breadboard layouts, plus annotated
photographs for what-it-actually-looks-like.** Defer to the user's
preference.

---

## 8. Open questions for the user

Before chapters are written, please decide:

1. **Solderless only, or solder-allowed?** Current plan assumes
   breadboard + jumper wires for the whole build. Some parts
   (74HC595 chain, MCP23017) are noticeably tidier on a soldered
   protoboard. Recommend solderless reference build with an Appendix D
   note about migration.
2. **Diagram tool.** See §7 — Fritzing is the recommended default.
3. **Photo source.** Will photos be taken on the user's bench during the
   real build, or sourced from the part vendors? Recommend taking
   photos during the actual build — they're more relatable.
4. **Multimeter — required tool or nice-to-have?** Current plan: nice-to-have.
   The chapter on troubleshooting (Ch 15) uses it for power-rail checks but
   the basic build doesn't depend on one.
5. **Voice for the AI in the manual examples.** Should the manual show
   a specific personality (e.g. Test Console) throughout, or switch
   between scenarios? Recommend Test Console only — keeps wiring
   chapters from being cluttered with scenario authoring.
6. **One reader or two?** Some chapters get safer/faster with two
   people (one to hold, one to wire). Should the manual call this out?
   Recommend yes, occasionally, but never as a requirement.
7. **Is the build supposed to be permanent or temporary?** A reusable
   "lab rig" version is more forgiving; a "make a real cosplay panel"
   version requires Chapter 13 (mounting). Both can be supported with
   Chapter 13 marked optional.

---

## 9. Chapter outlines

The detail level below is enough for a writer to begin drafting each
chapter without further input. Each entry lists: the chapter's question
to answer, the checkpoints the reader must hit, the new terms it
introduces (and that go into the glossary), and the diagrams it needs
(referenced by ID in `DIAGRAM_LIST.md`).

### Chapter 00 — Welcome & Safety

- **Question this chapter answers:** *What am I about to build, and how do I not hurt myself or the parts?*
- **Reader learns:** what the finished panel does; the 4 safety rules
  (no liquids, no mains voltage, ground yourself, USB-only power); the
  tool list; that no soldering is required for the reference build.
- **Checkpoint:** reader has all tools laid out and has touched a grounded
  metal object before opening any chip's packaging.
- **New terms:** ESD, USB-C, breadboard, jumper wire, multimeter (optional).
- **Diagrams:** D-0.1 tool photo array; D-0.2 finished panel preview.

### Chapter 01 — What You Already Have (Mini-AI Pi 5)

- **Question:** *What are all these parts on the desk?*
- **Reader learns:** to identify the Raspberry Pi 5, its 27 W USB-C
  power supply, the Yahboom mic/speaker, the Logitech webcam, the SSD.
- **Checkpoint:** every part in the parts list (Appendix A, §1) is
  identified by name.
- **New terms:** Raspberry Pi, single-board computer (SBC), USB peripheral.
- **Diagrams:** D-1.1 annotated photo of every existing part on a tray;
  D-1.2 USB-C power-supply close-up (showing the 27 W rating).

### Chapter 02 — Big Picture of the Control Panel

- **Question:** *How do all the new parts work together?*
- **Reader learns:** the four boxes — Pi 5 (brain), Metro RP2040 (panel
  brain), Nicla Voice (ear), Panel (switches/LEDs/displays/sound); how
  they connect (USB for the brains, wires for the panel); that the
  reader can test everything in their browser before plugging in any
  hardware.
- **Checkpoint:** reader can sketch the architecture diagram from memory.
- **New terms:** microcontroller (MCU), control panel, simulator, HAL.
- **Diagrams:** D-2.1 four-box architecture diagram; D-2.2 simulator
  screenshot.

### Chapter 03 — Setting Up Your Workspace

- **Question:** *Where do I do this work and how do I keep parts safe?*
- **Reader learns:** good vs bad work surfaces; what the breadboard's
  + and - rails are and how the internal connections run; how to insert
  a jumper without bending the leg; ESD precaution (touch grounded
  metal); how to take "progress photos" with their phone.
- **Checkpoint:** breadboard mounted, jumper wire kit organized, ESD
  habit established.
- **New terms:** rail, jumper wire, ESD wrist strap (optional).
- **Diagrams:** D-3.1 breadboard internal-connection diagram; D-3.2
  photo of organized workspace.

### Chapter 04 — Powering Things

- **Question:** *Where does the electricity come from?*
- **Reader learns:** voltage explained with water-pressure analogy;
  what 5 V and 3.3 V mean; why GND must be shared between every device;
  how to take 5 V and GND from the Pi 5 GPIO header to the breadboard
  rails using two female-to-male jumpers.
- **Checkpoint:** breadboard + rail lights up if a single LED + resistor
  is poked in (optional verification step).
- **New terms:** voltage, current, ground, GPIO header, common ground.
- **Diagrams:** D-4.1 Pi 5 40-pin header with 5 V and GND pins highlighted;
  D-4.2 breadboard rails after wiring; D-4.3 the "water pressure" voltage
  analogy.

### Chapter 05 — First Test — the Metro RP2040 Alone

- **Question:** *Can I get the panel's brain talking to my computer?*
- **Reader learns:** what CircuitPython is (Python that runs on chips);
  how to put the Metro into bootloader mode (hold BOOTSEL); how to drag
  a `.uf2` file; how the board reappears as `CIRCUITPY`; how to copy our
  firmware files; how to open a serial terminal (PuTTY on Windows,
  `screen` on macOS/Linux) at 115200 baud; what to expect.
- **Checkpoint:** reader sees `{"t":"hello",...}` and `{"t":"ready",...}`
  in the terminal. **First win.**
- **New terms:** CircuitPython, `.uf2`, bootloader, REPL, baud rate,
  serial terminal, JSON.
- **Diagrams:** D-5.1 BOOTSEL button location photo; D-5.2 file copy
  screenshot; D-5.3 serial terminal screenshot with the hello/ready
  frames highlighted.

### Chapter 06 — The Sound Module (CH358D)

- **Question:** *How do I make the panel play sounds?*
- **Reader learns:** what the CH358 does; how to generate the 10 WAVs
  using `python tools/generate_sfx.py`; how to copy them to the TF card
  by connecting the CH358's micro-USB to the computer; what a transistor
  is (an electronic switch); how to read the 2N3904 pinout (EBC vs
  CBE — depending on viewing angle); wiring one slot's transistor
  driver; how `enabled: True` in `config.py` and the firmware reload
  work; the CLI command to trigger.
- **Checkpoint:** running `python -m overlay.pi5_hal sfx 1` produces an
  audible ack chime.
- **New terms:** transistor, base/collector/emitter, NPN, active low,
  current-limiting resistor.
- **Diagrams:** D-6.1 CH358 module photo with K-pin labels;
  D-6.2 2N3904 pinout; D-6.3 wiring diagram for slot 1;
  D-6.4 photograph of the wired slot 1.

### Chapter 07 — Panel Display A — the 1602 LCD

- **Question:** *How do I get text onto a screen?*
- **Reader learns:** what I²C is (the "shared phone line" analogy: two
  wires, many devices, each with an address); the 1602 LCD's 4 pins
  (VCC, GND, SDA, SCL); default address (0x27 or 0x3F); how to find the
  address with an I²C scanner if needed (optional script); how to write
  text from the CLI.
- **Checkpoint:** the LCD shows `HELLO WORLD`.
- **New terms:** I²C bus, SDA, SCL, address, scanner.
- **Diagrams:** D-7.1 1602 LCD photo with pin labels; D-7.2 4-wire
  wiring diagram; D-7.3 photograph of working LCD with text.

### Chapter 08 — Panel Display B + Master — Two OLEDs

- **Question:** *How do I add more than one display on the same wires?*
- **Reader learns:** what an OLED is (different tech, sharper image);
  why both OLEDs ship at the same address (0x3C); the address jumper
  trick (solder pad, or solder bridge); wiring the second OLED in
  parallel; rendering a status block and an alert.
- **Checkpoint:** both OLEDs show different content from CLI commands.
- **New terms:** OLED, address jumper, parallel bus connection.
- **Diagrams:** D-8.1 OLED back showing address jumper; D-8.2 dual-OLED
  wiring; D-8.3 photograph of the working displays.

### Chapter 09 — Toggle Switches & MCP23017

- **Question:** *How does the AI know I flipped a switch?*
- **Reader learns:** that a microcontroller has limited pins, so we use
  an "I/O expander" to add more; the MCP23017 chip layout (16 pins on
  each side); inserting it across the breadboard center groove;
  wiring power + I²C + RESET + the 3 address pins (A0/A1/A2 = 000 → 0x20);
  what a "pull-up resistor" is (a wire that gently holds a pin HIGH so
  it's never floating); enabling internal pull-ups in firmware; wiring
  one toggle switch (one leg to MCP pin, other to GND); the "active low"
  convention.
- **Checkpoint:** flipping switch 1 in the simulator browser tab shows
  the corresponding event in the protocol log AND, if real switch is
  wired, flipping the real switch shows the same event.
- **New terms:** I/O expander, DIP package, pull-up resistor, active low,
  floating pin.
- **Diagrams:** D-9.1 MCP23017 pinout; D-9.2 wiring across breadboard
  center groove; D-9.3 single-switch wiring; D-9.4 photo of all 10 wired.

### Chapter 10 — LEDs & 74HC595 Shift-Register Chain

- **Question:** *How do I drive 50 LEDs from a few pins?*
- **Reader learns:** what a shift register is (the "conga line of
  outputs" analogy — push 8 bits in one wire at a time and they pop out
  on 8 pins); chaining 7 of them; LED polarity (long leg = anode,
  short leg = cathode, flat side of bulb = cathode); current-limit
  resistor value calculation (a simple Ohm's-law-by-example, no theory
  beyond "330 Ω works for most LEDs at 3.3-5 V"); inserting LEDs
  through a piece of perfboard or a panel template.
- **Checkpoint:** `python -m overlay.pi5_hal leds FF00FF00...` makes
  alternating LEDs light up.
- **New terms:** shift register, daisy-chain, anode, cathode, Ohm's law
  (just the formula and the example).
- **Diagrams:** D-10.1 74HC595 pinout; D-10.2 chain wiring (1 of 7
  chips, then the chain principle); D-10.3 LED polarity diagram;
  D-10.4 photograph of fully populated LED bank.

### Chapter 11 — PTT, PIR, MT-301 Key Switch

- **Question:** *How does the AI know I pressed the button, walked by, or turned the key?*
- **Reader learns:** the PTT button: a "momentary" switch with two legs
  — wire one to the MCP, one to GND, enable pull-up; the PIR sensor:
  3 wires (VCC, GND, OUT — directly to the MCP), with the trim-pot for
  sensitivity; the MT-301 key switch: explicit safety rules ("we are
  using only the auxiliary contacts at low voltage"), wiring SAFE and
  ARM contacts as separate inputs.
- **Checkpoint:** pressing PTT emits a `ptt` event, walking near the PIR
  emits a `pir` event, turning the key emits a `key` event with the new
  position.
- **New terms:** momentary switch (vs latching), passive infrared sensor
  (PIR), aux contact, arm gate, safety interlock.
- **Diagrams:** D-11.1 PTT button wiring; D-11.2 PIR sensor pinout;
  D-11.3 MT-301 contact diagram (with the explicit "low voltage only"
  callout); D-11.4 photograph of the wired inputs.

### Chapter 12 — The Always-On Ear — Arduino Nicla Voice

- **Question:** *How does the panel start listening when I say "computer"?*
- **Reader learns:** what Edge AI / TinyML is (one paragraph);
  the Nicla Voice has a tiny chip that's listening all the time but
  uses very little power; plugging the Nicla into the Pi 5 with USB;
  the Pi 5 sees it as a serial device; running the helper script that
  listens for `wake` and `intent` events; pointer to Edge Impulse for
  training your own keywords (only a pointer — not in scope).
- **Checkpoint:** saying the wake word causes the Pi 5 logs to show a
  `wake` event.
- **New terms:** Edge AI, TinyML, wake word, intent, NDP120.
- **Diagrams:** D-12.1 Nicla Voice annotated photo; D-12.2 USB
  connection to Pi 5; D-12.3 expected log output.

### Chapter 13 — Mounting Onto a Panel (Optional)

- **Question:** *How do I make it look like a real control panel?*
- **Reader learns:** simple panel options (foam board, plywood, 3D-print);
  drilling holes for toggle switches and the key; LED mounting with
  bezels; cable strain relief; labelling with a label-maker or
  print-and-stick decals.
- **Checkpoint:** all parts attached to a panel; cables don't dangle.
- **New terms:** strain relief, panel-mount.
- **Diagrams:** D-13.1 panel layout template (a single-sheet PDF the
  reader can print); D-13.2 example finished panels.

### Chapter 14 — First Real Run

- **Question:** *Does the whole thing actually work?*
- **Reader learns:** the power-on order (Pi 5 first, then the Metro;
  the Nicla is fine plugged in last); how to open the simulator browser
  tab as a "scope" view of the panel state in real time; how to run
  `python -m overlay.scenario.demo --repl`; how to talk to the AI; what
  to listen for and watch for; how to switch between scenarios when
  multiple are authored (forward reference to Drop 3+).
- **Checkpoint:** spoken request to the AI produces the expected panel
  actions and a spoken reply. **Build complete.**
- **New terms:** REPL (interactive prompt), scenario.
- **Diagrams:** D-14.1 final wired panel + Pi 5 photo; D-14.2 demo
  terminal screenshot.

### Chapter 15 — Troubleshooting

- **Question:** *What do I do when something doesn't work?*
- **Reader learns:** a symptom-cause-fix table covering the 30+ most
  common issues; how to use a multimeter to check the 5 V rail (the one
  troubleshooting step where a multimeter is genuinely useful); how to
  read the simulator's protocol log to see what messages were sent /
  received; how to ask for help (which logs to copy, which photos to
  take).
- **Checkpoint:** reader can resolve at least the 3 most common issues
  on their own.
- **New terms:** symptom, root cause.
- **Diagrams:** D-15.1 multimeter on the 5 V rail; D-15.2 protocol log
  with annotations.

### Appendix A — Bill of Materials

See [`BILL_OF_MATERIALS.md`](BILL_OF_MATERIALS.md).

### Appendix B — Pinout Reference Card

One printable PDF page covering: Metro RP2040 pin map, MCP23017
connections, 74HC595 daisy-chain, I²C addresses in use, CH358 K-pin
mapping. Designed to live next to the bench.

### Appendix C — Glossary

A-Z. ~50 entries pulled from the "New terms" lines above. Each entry is
two sentences: the definition, and a back-link to the chapter where it
was introduced.

### Appendix D — Going Further

Five forks the curious reader can take after finishing the manual:
1. **Author a new scenario.** Points to `overlay/scenario/README.md`.
2. **Add a new sound.** Edit `canonical/sfx_bank.yaml` (limited to 10
   slots; how to reassign).
3. **Train your own Nicla wake word.** Edge Impulse pointer.
4. **Migrate the build to a soldered protoboard.** What changes, what
   doesn't.
5. **Add the GIGA Display Shield as a touch scenario-selector.** What
   else you'd need to buy (the GIGA R1).

---

## 10. Production schedule

| Step | Output | Estimated effort |
|---|---|---|
| 1 | Review of this plan + answers to the 7 open questions in §8 | 1 sitting |
| 2 | Chapter 0 + Chapter 1 + Appendix A (BOM made user-facing) | 1 sitting |
| 3 | Chapters 2–4 (orientation chapters) | 1–2 sittings |
| 4 | Chapter 5 + Chapter 6 — the "first wins" — drafted **at the bench** while doing the build for real | 1 long sitting |
| 5 | Chapters 7–8 — displays | 1 sitting |
| 6 | Chapter 9 + Chapter 10 — switches + LEDs | 1–2 sittings |
| 7 | Chapter 11 + Chapter 12 — inputs + Nicla | 1 sitting |
| 8 | Chapter 13 + Chapter 14 — mounting + first run | 1 sitting |
| 9 | Chapter 15 — troubleshooting (populated *after* the build, from real failures encountered) | 1 sitting |
| 10 | Appendices B–D + final read-through | 1 sitting |

Total: ~10–12 sittings. Roughly half the writing is done **at the bench
during the real build** — that's where the realistic checkpoints,
gotchas, and "this is what it actually looks like" photos come from.
That's also why writing earlier chapters first (which are
build-independent) reduces wasted work.

---

## 11. What to do next

1. Read this plan; answer the 7 open questions in §8.
2. Skim [`BILL_OF_MATERIALS.md`](BILL_OF_MATERIALS.md) and approve the
   procurement gaps (the manual can't be written without those parts on
   the bench).
3. Skim [`STYLE_GUIDE.md`](STYLE_GUIDE.md) and adjust tone/format
   preferences.
4. Approve the chapter list. Each chapter draft will be a separate
   commit so you can review and revise without waiting for the whole
   manual.
