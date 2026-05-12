# Bill of Materials — mini-ai hardware build

Every part the build needs, split into three groups:

1. **In inventory** — already on hand, no action required.
2. **To procure** — the build cannot proceed without these.
3. **Optional / future** — nice-to-have, deferred, or unlocked by
   additional procurement.

Costs are approximate USD list prices from common hobbyist retailers
(Adafruit, DigiKey, Mouser, Amazon, AliExpress) as of late 2025/2026.
The build does not require any single source — substitutions are noted
where they're safe.

---

## 1. In inventory (no action)

### 1.1 The existing mini-ai-pi build

| Part | Role | Notes |
|---|---|---|
| Raspberry Pi 5, 16 GB         | The AI brain. Runs Whisper, Ollama, Piper. | Already running per the existing `setup_all.py` flow. |
| Official Pi 5 27 W USB-C PSU  | Powers the Pi 5. | **Required to be 27 W.** 15 W and 2.5 A supplies cause silent failures. |
| 2 TB USB-NVMe or NVMe-on-HAT  | OS and model storage. | Either USB enclosure or PCIe HAT works. |
| Yahboom YB-MAE02-V1.0 mic/spkr | USB mic array + speaker. | Reused for Piper TTS output. |
| Logitech C920 USB webcam      | Optional vision input. | Used by existing vision path, not by the panel. |

### 1.2 Control-panel parts already on the bench

| Part | Role in panel | Notes |
|---|---|---|
| Adafruit Metro RP2040          | Panel brain (runs CircuitPython firmware). | USB-C; 26 GPIO; Arduino UNO form factor. |
| Arduino Nicla Voice (ABX00061) | Always-on wake-word + keyword detection. | NDP120 inference, very low power. |
| Inland PIR motion sensor       | Presence/motion input. | 3-wire (VCC, GND, OUT). |
| Inland 1602 I²C LCD            | Panel display A (telemetry text). | I²C backpack, default address 0x27. |
| Adafruit #938 OLED 128×64      | Panel display B (graphics). | I²C, default address 0x3C. |
| STEMMA QT 128×64 OLED          | Master status display. | I²C; **address jumper changed to 0x3D** during build. |
| CH358D-TF-1G sound module      | 10-slot hardware SFX player. | TF card up to 1 GB; trigger pins K1–K10. |
| MT-301R4P-P key isolator switch | Safety arm gate. | **Auxiliary contacts only at low voltage.** |
| 50+ toggle switches (various)  | Panel inputs. | Mix of SPST/SPDT. Use any 10 visually consistent ones for panel slots S1–S10. |
| 50+ LEDs (various colors)      | Panel output. | Through-hole, 5 mm or 3 mm. 50 needed for the bank. |
| Spare Raspberry Pi 4           | Reserved for future use. | Not used in the build manual; see Drop notes. |

### 1.3 Tools likely already on hand

Bench / lab basics. Most are owned by anyone with prior maker
exposure; the manual will tell first-timers what to acquire.

| Item | Required? |
|---|---|
| USB-C cable (data, not power-only) | yes |
| USB-A cable for the Nicla         | yes |
| Small Phillips screwdriver        | yes |
| Side cutters                      | yes |
| Wire strippers                    | yes |
| **Camera or phone for progress photos** | yes — the deployment already includes multiple cameras (Logitech C920 on the Pi, plus any phone or other camera the builder has); photos are taken in-house |
| **Multimeter** | **yes — required** (see §8 decision #4 in BUILD_MANUAL_PLAN.md). Used in Chapter 4 to confirm the 5 V rail, in Ch 9 for switch continuity, in Ch 10 for LED-resistor sanity checks, and throughout Ch 15 troubleshooting. A $20 entry-level meter is fine. |

---

## 2. To procure (build blocked without these)

### 2.1 Core electronic components

| Part | Qty | Why | Approx unit | Vendor examples |
|---|---|---|---|---|
| **MCP23017 16-bit I²C I/O expander** (DIP-28) | 1 | Adds the 12 inputs the build needs (10 switches + 2 key positions); the Metro alone has too few free pins after I²C, SFX drivers, and the LED chain. | $3 | Adafruit #732, DigiKey, Mouser |
| **74HC595 8-bit shift register** (DIP-16) | 7 | Drives the 50 LEDs from 3 wires. 7 × 8 = 56 outputs (50 used). | $1 | Adafruit #450 (5-pack), DigiKey |
| **2N3904 NPN transistor** (TO-92) | 10 | One per CH358 K-pin driver. | $0.10 | Common multi-packs from Amazon / AliExpress |
| **330 Ω resistors** (¼ W) | 60 | Current-limit per LED. | $0.02 | Value-pack of through-hole resistors |
| **4.7 kΩ resistors** (¼ W) | 20 | Transistor base resistors + pull-ups. | $0.02 | Same value-packs |
| **Solderless breadboard, full-size** (830-point) | 2 | Phase-1 breadboard build (Ch 5–12). | $5 | Standard clone |
| **Jumper wire kit** (M-M + M-F, 65-pc minimum) | 1 | Breadboard connections. | $10 | Any vendor |
| **PTT button** (momentary, panel-mount, 30 mm preferred) | 1 | The push-to-talk button. | $5 | Adafruit #1185 or AliExpress |
| **Small speaker for CH358** (8 Ω, ½–1 W) | 1 | Driven directly by the CH358 module so panel SFX don't fight the Yahboom speaker (which is dedicated to Piper TTS). Additional speakers can be added later for stereo or zoned audio (Appendix D). | $3 | Adafruit #1313 |
| **TF (microSD) card** (8 GB Class 10 is fine; some CH358 builds want ≤ 1 GB — try the larger first, fall back if it doesn't enumerate) | 1 | Holds the 10 WAVs for the CH358. | $5 | Any vendor |

### 2.2 Soldering supplies (Chapter 13)

Per §8 decision #1: build is breadboard-first, then migrated to a
soldered perfboard for permanent installation. The reader is assumed
to have **never soldered before**, so the kit covers learning + the
real build.

| Part | Qty | Why | Approx unit | Notes |
|---|---|---|---|---|
| **Temperature-controlled soldering iron** (Pinecil V2, TS80P, Hakko FX-888D, or similar) | 1 | Temperature control is what separates "frustrating" from "easy." Avoid fixed-temperature plug-in irons. | $30–80 | Pinecil V2 (~$30) is the sweet spot for hobbyist learning. |
| **Soldering iron stand with sponge or brass-wool tip cleaner** | 1 | Iron must rest somewhere when not in hand. Brass wool is better than wet sponge for tip life. | $10 | Many irons ship with a stand; check before buying separately. |
| **Lead-free solder, 0.6 mm or 0.8 mm, rosin core** | 1 spool | Lead-free is safer for a young builder; 0.6–0.8 mm gauge is right for through-hole. | $15 | Sn99/Cu0.7/Ag0.3 alloys work well. |
| **Liquid or paste flux** | 1 small bottle | Helps solder flow; the rosin in the solder is usually enough, but flux saves bad joints. | $5 | No-clean variety preferred. |
| **Desoldering wick (braid)** | 1 roll | For removing solder when fixing mistakes. | $5 | 2 mm width is versatile. |
| **Desoldering pump ("solder sucker")** | 1 | Faster than wick for large blobs. | $7 | Manual spring type is fine. |
| **Helping-hands stand** (alligator clips + magnifier optional) | 1 | Holds parts and boards while you solder. Critical when alone (the manual's TWO-PERSON callouts mostly disappear if this is on the bench). | $10–25 | Magnifier version recommended for fine work. |
| **Perfboard / protoboard** (2.54 mm pitch, double-sided plated through-hole, ~7 × 9 cm) | 4 | 1 for the brains, 1 for the LED bank, 1 for the I²C hub, 1 spare. | $2 ea | Either prototyping perfboard or stripboard works; perfboard is more flexible. |
| **Single-row male header pins** (40-pin strips, 2.54 mm) | 5 strips | Mounting boards onto the perfboard with sockets; also for the CH358 daughter-card connection. | $1 ea | Snap to length with side cutters. |
| **Single-row female header sockets** (40-pin strips) | 3 strips | The matching sockets for the male pins above. | $1.50 ea | |
| **PCB-mount screw terminals** (2-pin and 3-pin, 5.08 mm pitch) | 10 pcs | Connect panel-mounted parts (switches, key, PTT, PIR) to the perfboard with stranded wire. | $0.50 ea | Phoenix-style green terminals. |
| **Solid-core hookup wire**, 22 AWG, several colours (red, black, yellow, blue, green, white at minimum) | 1 small spool each | Board-to-board jumpers on perfboard, matching the manual's wire-colour convention. | $5 ea | A pre-cut assortment box (around $15) is convenient. |
| **Stranded hookup wire**, 22 AWG, same colours | 1 small spool each | Board-to-panel runs (more flexible than solid). | $5 ea | |
| **Heat-shrink tubing assortment** (1.5–6 mm, mixed colours) | 1 kit | Insulating every exposed splice on the panel-side wiring. | $10 | Heat from the soldering iron or a hair-dryer at 100 °C+ shrinks it. |
| **Crimp ferrules** (assortment, for 22 AWG) | 1 small bag | Crimp on stranded-wire ends before inserting into screw terminals — much more reliable than bare-wire-into-terminal. | $8 | Pair with a cheap crimp tool ($15) if you don't already own one. |
| **Crimp ferrule tool** | 1 | Crimps the ferrules above. | $15 | Optional but recommended. |
| **Brass-wool refill** | 1 | Replacement for tip cleaner (lasts months but worth having). | $3 | |
| **Safety glasses** | 1 pair | Solder occasionally splatters. Eyes deserve protection. | $5 | **Not optional.** Manual's WARNING callout will reinforce. |
| **Small clip-on USB fume fan** (or a regular fan blowing across the bench, away from face) | 1 | Lead-free solder fumes are mostly flux smoke — keep it out of the lungs. | $10–20 | Even a desk fan helps. |

### 2.3 Permanent mounting hardware (Chapter 13.C)

| Part | Qty | Why | Approx unit | Notes |
|---|---|---|---|---|
| **Panel material** — your choice of one of: acrylic sheet (6 mm, ~30 × 40 cm), plywood (6 mm, same), or aluminium (3 mm) | 1 sheet | The actual front panel of the build. | $10–30 | The manual will recommend acrylic for ease + look; plywood for cheap+easy; aluminium for premium. |
| **M3 screws + nuts** (10 mm and 16 mm length) | 30 ea | Mounting boards and components to the back of the panel. | $5 (assortment bag) | |
| **M3 brass standoffs / spacers** (10 mm and 20 mm, M-F) | 20 | Hold perfboards off the panel back with airflow. | $10 (assortment) | |
| **LED bezels / holders** (5 mm chromed plastic — pick a colour) | 50 | Make the panel-mounted LEDs look intentional rather than poked-through. | $0.10 ea | $5 for 50. |
| **Cable ties / zip ties** (small + medium) | 1 bag of each | Cable management on the back of the panel. | $5 | |
| **Stick-on cable mounts** (with double-sided foam tape) | 1 small pack | Anchoring cable bundles. | $5 | |
| **Hot glue gun + glue sticks** (low-temperature 100 °C variant preferred) | 1 | Quick non-structural mounting (e.g. holding the PIR module behind a panel window). | $10 | Optional but useful. |
| **Adhesive labels** OR a **Brother PT-D210 label maker + tape** | 1 of either | Labelling switches per the active scenario. Stick-on printable labels are cheaper; a label maker is faster for many labels. | $5 / $30 | Label maker recommended given the number of labels. |
| **Print-and-stick decal sheet** (Avery 8167 or similar, for the home printer) | 1 pack | Backup option to the label maker. | $10 | |

### 2.4 Recommended spares (per §8 decision #9)

The user has confirmed spare parts are welcome. These quantities make
the build forgiving of the inevitable burnt LED, lost jumper, or
"oops the smoke came out" moment. **Skip any you already have in
abundance.**

| Part | Suggested spare qty | Why |
|---|---|---|
| MCP23017                          | 1 extra (2 total)   | If you damage the original or want a second one for an expanded panel later. |
| 74HC595                            | 2 extras (9 total)  | These chips are cheap and shift-register chains are unforgiving of damaged outputs. |
| 2N3904                             | 10 extras (20 total) | Easy to install backwards; through-hole transistors are <$0.10 each. |
| LEDs (each colour you bought)      | 10 extras per colour | Some will inevitably get bent, reversed, or smoked. |
| 330 Ω + 4.7 kΩ resistors           | 50 extras each      | Cheaper as part of a 600-piece resistor-assortment kit (~$15) than singles. |
| Hookup wire                        | +1 spool of each colour | You will use more than you expect. |
| Heat-shrink tubing                 | extra of the small sizes | The 1.5–3 mm sizes go fastest. |
| Soldering iron tips                | 1 spare conical tip | Tips wear out; having a spare avoids a stalled build. |
| Solder                             | 1 spare 100 g spool | A second spool is months of supply. |
| Header pins / sockets              | 2 spare strips each | |
| Perfboard                          | 2 extras (6 total)  | Mistakes happen on the first attempt at a layout. |
| Jumper wires                       | extra 30-piece kit  | Loose wires under the desk are a fact of life. |
| Breadboard                         | 1 spare half-size   | Useful for testing a single new module in isolation. |

**Subtotal of recommended spares: ~$40.**

### 2.5 Estimated procurement total

| Section | Subtotal |
|---|---|
| 2.1 Core electronic components       | ~$50  |
| 2.2 Soldering supplies               | ~$150–200 (assumes iron must be bought; ~$80 if a working iron is already owned) |
| 2.3 Permanent mounting hardware      | ~$60  |
| 2.4 Recommended spares               | ~$40  |
| **Total procurement (worst case)**   | **~$300–350** |
| **Total if soldering iron already owned + restrained spares** | **~$200** |

### Substitutions / cheaper paths

- **MCP23017 vs PCF8574**: an 8-bit PCF8574 (single chip, ~$2) can
  cover 8 switches + leave the key on direct GPIO. The manual will use
  MCP23017 because it covers all 12 inputs in one chip and matches
  what's standardized in `overlay/firmware/rp2040/config.py`.
- **74HC595 vs WS2812 (NeoPixel) strip**: a 50-LED NeoPixel strip
  costs more (~$20) but eliminates the chain wiring. The manual uses
  74HC595 because the through-hole LEDs are already in inventory.
- **Real toggle switches vs tact-button-only first build**: a builder
  could prototype with 10 tactile pushbuttons instead of toggles to
  defer panel mounting until later. The manual assumes toggles.
- **Soldering iron**: any temperature-controlled iron works. If a
  Hakko or Weller is already on hand, use it — no need for the Pinecil.
- **Perfboard vs stripboard ("Veroboard")**: stripboard has copper
  tracks already running across rows; you cut tracks where you don't
  want connections. The manual will use plain perfboard because the
  connections are explicit and easier to trace in a diagram for a
  first-time builder. A reader can substitute stripboard if comfortable.

---

## 3. Optional / future

| Part | Use | Status |
|---|---|---|
| **Arduino GIGA R1 WiFi**              | Host for the GIGA Display Shield (touch scenario-selector UI). | Procure if/when the touch UI path is desired; ~$80. |
| **Arduino GIGA Display Shield (ASX00039)** | Already in inventory; needs the R1 host. | In inventory, deferred. |
| **Edge Impulse account**              | Train custom Nicla wake-word + keyword models. | Free tier sufficient; pointer in Appendix D. |
| **Second CH358 module**               | Per-scenario SFX banks instead of one universal bank. | Deferred — universal SFX bank is the design choice for now. |
| **MCP23017 breakout board (Adafruit #5346)** | Same chip but easier to wire (no DIP-on-breadboard fiddling). | Substitute for the bare chip if preferred — ~$8 vs ~$3. |
| **Anti-static wrist strap**           | Strictly safer chip handling. | $5; manual treats it as recommended but not mandatory. |
| **Additional speakers**               | Stereo or scenario-zoned audio (e.g. one speaker per console area). | Per §8 decision #8; the deployment already has the Yahboom for Piper TTS and one small speaker for the CH358 — more can be added later. Mentioned in Appendix D. |
| **Project enclosure for the brain boards** | Houses the Pi 5, Metro RP2040, and Nicla behind the panel. Adds dust protection and a finished look. | A 3D-printed or wooden box; designs can be sourced or made. ~$15–40. Optional but suggested in Chapter 13.C as a follow-on. |
| **Powered USB hub** | If the back-of-panel cable run between Pi 5 and the Metro/Nicla becomes long, a powered hub helps with reliability. | ~$20. Mentioned in Ch 13 if relevant. |

---

## 4. Total cost (all-in, from a hypothetical zero-inventory start)

| Bucket | Cost |
|---|---|
| Pi 5 + 27 W PSU + 2 TB SSD                          | ~$130 |
| Yahboom mic/speaker                                  | ~$30  |
| C920 webcam                                          | ~$70  |
| Metro RP2040                                         | ~$15  |
| Arduino Nicla Voice                                  | ~$80  |
| Inland PIR                                           | ~$5   |
| 1602 LCD with I²C backpack                           | ~$8   |
| Adafruit #938 OLED                                   | ~$18  |
| STEMMA QT 128×64 OLED                                | ~$18  |
| CH358D-TF-1G                                         | ~$10  |
| MT-301R4P-P                                          | ~$30  |
| 10 toggle switches                                   | ~$15  |
| 50 LEDs                                              | ~$10  |
| Section 2.1 core electronic components               | ~$50  |
| Section 2.2 soldering supplies (kit + iron)          | ~$150–200 |
| Section 2.3 permanent mounting hardware              | ~$60  |
| Section 2.4 recommended spares                       | ~$40  |
| **Total estimated cost (worst case, zero inventory)** | **~$740–790** |

**The user already has everything in Section 1.** Realistic additional
spend, given the §8 decisions:

| Scenario | Procurement |
|---|---|
| Already own a temperature-controlled soldering iron; modest spares | **~$200** |
| Need to buy the soldering iron + generous spares                    | **~$300–350** |

---

## 5. Notes for the manual author

- **Photograph every part on a labelled tray** before Chapter 1 is
  written. A photo with every part in inventory clearly labelled is the
  single most useful illustration in the entire manual.
- **Order ahead.** Section 2 parts should be ordered before the bench
  writing begins. The wait kills momentum.
- **Buy 2× of the small consumables** (resistors, jumpers, LEDs). You
  *will* burn one out or lose one under the desk. Manual should
  acknowledge this normality (the Section 2.4 spares list addresses
  this, but the manual prose should also normalize it).
- **Don't conflate breadboard and perfboard photos.** Chapters 5–12
  document the breadboard build. Chapter 13 documents the migration to
  perfboard. The reader needs to see *both* — same circuit, different
  substrate — so they understand what's being preserved across the
  migration.
- **Solder once, ship forever.** Once a perfboard module is soldered
  in Chapter 13, it's not coming apart easily. Any layout changes the
  manual recommends should be locked in BEFORE Chapter 13 is written
  on the real bench. The first author drafting Chapter 13 needs to
  have rebuilt the breadboard correctly in chapters 5–12 first.
