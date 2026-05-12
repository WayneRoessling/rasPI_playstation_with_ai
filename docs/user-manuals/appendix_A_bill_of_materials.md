# Appendix A — Bill of Materials

This appendix is your shopping list and inventory in one place. It's organized into three sections:

1. **What you already have** — the parts that came with the existing mini-ai system.
2. **What to buy** — the parts you'll need before the panel build can proceed.
3. **What's optional** — nice extras you can add later or skip entirely.

Costs are in US dollars and approximate. Substitutions are noted where they're safe to make. You don't need to buy from any particular vendor — the parts are widely available from Adafruit, DigiKey, Mouser, Amazon, and AliExpress.

If you want the engineering-style version of this list, see [`plan/BILL_OF_MATERIALS.md`](plan/BILL_OF_MATERIALS.md). The version below is friendlier and skips the "subtotals" bookkeeping.

---

## 1. What you already have

### 1.1 The mini-ai-pi system

| Part | What it does | Notes |
|---|---|---|
| **Raspberry Pi 5 (16 GB)** | The "brain" — runs the speech recognition, language model, and text-to-speech. | The 16 GB version. Lower-RAM versions exist but won't run the full AI well. |
| **27 W USB-C power supply** | Powers the Pi. | Must be 27 W. A weaker brick causes random failures. |
| **2 TB SSD (in USB or HAT enclosure)** | Storage for the AI models. | The models are several gigabytes each, so big storage is the norm. |
| **Yahboom YB-MAE02-V1.0 mic/speaker** | The microphone you talk into and the main speaker. | USB. Plug-and-play. |
| **Logitech C920 webcam** | Optional vision input (for "describe what you see" features). | Not used by the panel itself. |

### 1.2 Panel parts already on the bench

| Part | What it does | Notes |
|---|---|---|
| **Adafruit Metro RP2040** | The panel's brain. | About the size of an Arduino. Runs CircuitPython. |
| **Arduino Nicla Voice** | The always-on ear that listens for the wake word. | Postage-stamp size. |
| **Inland PIR motion sensor** | Detects when someone walks by the panel. | Three-wire module. |
| **Inland 1602 I²C LCD** | The text-display panel ("HELLO WORLD" type). | Two rows, 16 characters each. |
| **Adafruit #938 OLED 128×64** | One of the two graphical displays. | Sharper than the LCD. |
| **STEMMA QT 128×64 OLED** | The other graphical display ("master status"). | Same screen, different connector style. |
| **CH358D-TF-1G sound module** | Plays canned sound effects from a memory card. | 10 sound slots; triggered by single pins. |
| **MT-301R4P-P key switch** | The "arm" key on the panel. | Industrial part — but you'll only use its low-voltage contacts. |
| **50+ toggle switches** | The panel's row of physical switches. | You'll use 10 visually consistent ones. |
| **50+ LEDs** | The panel's row of indicator lights. | Mix of colours; 50 in the panel. |
| **Spare Raspberry Pi 4** | Not used in this manual. | Set aside. |

### 1.3 Tools you should have

| Item | Required? |
|---|---|
| USB-C cable that carries data (not power-only) | Yes |
| USB-A cable for the Nicla Voice | Yes |
| Small Phillips screwdriver | Yes |
| Side cutters | Yes |
| Wire strippers | Yes |
| Phone or camera for progress photos | Yes |
| **Multimeter** (a basic $20 model is fine) | **Yes — required.** Used in Chapter 4 to verify the 5 V rail, in Chapter 9 for switch continuity, in Chapter 10 for LED sanity checks, and throughout Chapter 15 troubleshooting. |

---

## 2. What you need to buy

Total roughly **$300** for the full kit including soldering supplies, spares, and panel-mounting hardware. **About $200** if you already own a temperature-controlled soldering iron. The build cannot proceed without the parts in section 2.1; the rest can be ordered as you get to those chapters.

### 2.1 Core electronic components — about $50

| Part | Qty | What it does | Approx cost |
|---|---|---|---|
| **MCP23017 16-bit I²C I/O expander** (DIP-28) | 1 | A chip that gives you 16 extra input/output pins, used for the 10 switches and the key. | $3 |
| **74HC595 8-bit shift register** (DIP-16) | 7 | A chip that lets you drive lots of LEDs from a few control wires. 7 of them gives you 56 outputs — plenty for 50 LEDs. | $1 each |
| **2N3904 NPN transistor** (TO-92 package) | 10 | Tiny electronic switches that let the Metro fire each of the 10 sound slots. | $0.10 each |
| **330 Ω resistors** (¼ W) | 60 | Limits current through each LED so it doesn't burn out. | Cheaper in value packs |
| **4.7 kΩ resistors** (¼ W) | 20 | Used with the transistors and as pull-ups for switches. | Cheaper in value packs |
| **Solderless breadboard** (full-size, 830-point) | 2 | The plastic board you wire everything onto for the prototype build. | $5 each |
| **Jumper wire kit** (male-male + male-female, at least 65 pieces) | 1 | Pre-cut wires for breadboard connections. | $10 |
| **PTT button** (momentary, panel-mount, 30 mm) | 1 | The push-to-talk button. | $5 |
| **Small speaker for the CH358 sound module** (8 Ω, ½–1 W) | 1 | Plays the sound effects so they don't fight the Yahboom speaker. | $3 |
| **TF (microSD) card** (8 GB Class 10 is fine; some CH358 builds want ≤ 1 GB) | 1 | Holds the 10 sound-effect files. | $5 |

### 2.2 Soldering supplies — about $150 with iron, $80 without

You'll use these in Chapter 13 when migrating the breadboard build to a permanent soldered board.

| Part | What it does | Approx cost |
|---|---|---|
| **Temperature-controlled soldering iron** (Pinecil V2, TS80P, Hakko FX-888D) | The most important single tool in this section. Temperature control matters. | $30–80 |
| **Soldering iron stand with brass-wool tip cleaner** | A safe parking spot for the iron and a way to clean the tip. | $10 |
| **Lead-free solder, 0.6 mm or 0.8 mm, rosin core** | The metal that joins parts together. Lead-free is safer for a young builder. | $15 |
| **Liquid or paste flux** | Helps the solder flow cleanly. | $5 |
| **Desoldering wick (braid)** | Removes solder when fixing mistakes. | $5 |
| **Desoldering pump ("solder sucker")** | Sucks up large blobs of solder. | $7 |
| **Helping-hands stand** (with alligator clips and a magnifier) | Holds parts steady while you solder. | $10–25 |
| **Perfboard** (2.54 mm pitch, ~7 × 9 cm, plated through-hole) | 4 | The permanent replacement for the breadboard. | $2 each |
| **Male header pin strips** (40 pins, 2.54 mm) | 5 strips | Mounting pins so you can socket the Metro into the perfboard. | $1 each |
| **Female header sockets** (40-pin strips) | 3 strips | Matching sockets for the male pins. | $1.50 each |
| **PCB-mount screw terminals** (2 and 3 pin, 5.08 mm) | 10 | Where panel-mounted parts plug into the perfboard. | $0.50 each |
| **Solid-core hookup wire**, 22 AWG, in red, black, yellow, blue, green, white | 1 small spool each | Board-to-board jumpers. | $5 each |
| **Stranded hookup wire**, same colours | 1 small spool each | More flexible — for runs to panel-mounted parts. | $5 each |
| **Heat-shrink tubing assortment** (1.5–6 mm, mixed colours) | 1 kit | Insulates every exposed splice. | $10 |
| **Crimp ferrules + crimp tool** | 1 small bag + 1 tool | Crimps a clean end on stranded wires before they go into screw terminals. | $8 + $15 |
| **Safety glasses** | 1 pair | Eye protection — not optional when soldering. | $5 |
| **Small clip-on fume fan** | 1 | Keeps solder fumes away from your face. | $10–20 |

### 2.3 Permanent mounting hardware — about $60

For Chapter 13.C, once the perfboards are built and you're moving onto the final panel.

| Part | What it does | Approx cost |
|---|---|---|
| **Panel material** — acrylic, plywood, or aluminium (about 30 × 40 cm) | The front of the panel. | $10–30 |
| **M3 screws + nuts** (10 mm and 16 mm) | 30 each | Mount boards to the panel back. | $5 |
| **M3 brass standoffs** (10 and 20 mm, M-F) | 20 | Hold the perfboards off the panel back. | $10 |
| **LED bezels** (5 mm chromed plastic) | 50 | Make the panel-mounted LEDs look finished. | $5 |
| **Cable ties** (small + medium) | 1 bag each | Tidy the wires behind the panel. | $5 |
| **Stick-on cable mounts** | 1 small pack | Anchor cable bundles. | $5 |
| **Hot glue gun + sticks** (low-temp 100 °C variant) | 1 | Quick non-structural mounting. | $10 |
| **Adhesive labels** OR **a Brother label maker + tape** | 1 | Label the panel switches. | $5 or $30 |

### 2.4 Recommended spares — about $40

Stuff breaks during a first build. These spares keep you moving instead of waiting for shipping.

| Part | Suggested spare quantity | Why |
|---|---|---|
| MCP23017 | 1 extra | A second one is useful if you damage the first or want to expand later. |
| 74HC595 | 2 extras | Cheap chips; chains are unforgiving of damaged outputs. |
| 2N3904 transistors | 10 extras | Easy to put in backwards on the first try. |
| LEDs (each colour you bought) | 10 extras per colour | Some will get bent, reversed, or burnt out. |
| 330 Ω and 4.7 kΩ resistors | 50 extras each | Often cheaper to buy a 600-piece variety kit (~$15). |
| Hookup wire | 1 spare spool of each colour | You'll use more than you expect. |
| Heat-shrink tubing | Extra small sizes | The 1.5–3 mm sizes go fastest. |
| Soldering iron tips | 1 spare conical tip | Tips wear out. |
| Solder | 1 spare 100 g spool | Many months of supply. |
| Header pins / sockets | 2 spare strips each | |
| Perfboard | 2 extras | Layout mistakes happen. |
| Jumper wires | 1 extra 30-piece kit | Loose wires under the desk are normal. |
| Breadboard | 1 spare half-size | Useful for testing one module in isolation. |

---

## 3. Optional / future

| Part | What it does | Notes |
|---|---|---|
| **Arduino GIGA R1 WiFi + GIGA Display Shield** | A touch screen for picking scenarios. | About $80 for the R1; the Display Shield is already in inventory. |
| **Edge Impulse account** (free tier) | Train your own Nicla wake-words and keywords. | Pointer only — Appendix D. |
| **Second CH358 module** | Per-scenario sound banks instead of one universal bank. | Deferred; one bank is the design for now. |
| **MCP23017 breakout board** (Adafruit #5346) | Same chip with the wiring already done. | About $8 vs $3 for the bare chip. Easier for absolute beginners. |
| **Anti-static wrist strap** | Belt-and-braces ESD protection. | $5. Optional but recommended. |
| **Additional speakers** | Stereo or zoned audio. | The build ships with one CH358 speaker; more can be added. |
| **Project enclosure for the brain boards** | Houses the Pi 5, Metro, and Nicla behind the panel. | $15–40, optional. |
| **Powered USB hub** | Useful if cable runs get long. | About $20. |

---

## Quick links to detailed plan documents

- [`plan/BILL_OF_MATERIALS.md`](plan/BILL_OF_MATERIALS.md) — engineering-style version of this list with substitution notes and total-cost tables.
- [`plan/BUILD_MANUAL_PLAN.md`](plan/BUILD_MANUAL_PLAN.md) — what each chapter covers and which parts each one uses.
- [Chapter 1 — What you already have](01_what_you_already_have.md) — guided tour of the parts in section 1 above.
