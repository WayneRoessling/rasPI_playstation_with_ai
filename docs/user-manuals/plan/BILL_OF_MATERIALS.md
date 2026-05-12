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
| Phone or camera for progress photos | yes |
| Multimeter                        | nice to have (Ch 15 only) |

---

## 2. To procure (build blocked without these)

| Part | Qty | Why | Approx unit | Vendor examples |
|---|---|---|---|---|
| **MCP23017 16-bit I²C I/O expander** (DIP-28 package) | 1 | Adds the 12 inputs the build needs (10 switches + 2 key positions); the Metro alone has too few free pins after I²C, SFX drivers, and the LED chain. | $3 | Adafruit #732, DigiKey, Mouser |
| **74HC595 8-bit shift register** (DIP-16 package) | 7 | Drives the 50 LEDs from 3 wires. 7 × 8 = 56 outputs (50 used). | $1 | Adafruit #450 (5-pack), DigiKey |
| **2N3904 NPN transistor** (TO-92 package) | 10 | One per CH358 K-pin driver. | $0.10 | Common multi-packs from Amazon / AliExpress |
| **330 Ω resistors** (¼ W) | 60 | Current-limiting per LED (50) + spares. | $0.02 | Any value-pack of through-hole resistors |
| **4.7 kΩ resistors** (¼ W) | 20 | Transistor base resistors + I²C pull-ups (if needed) + spares. | $0.02 | Same value-packs |
| **Solderless breadboard, full-size** (830-point) | 2 | One for the brains/expanders/CH358 drivers, one for the LED bank. | $5 | Standard cheap clone is fine |
| **Jumper wire kit** (male-male + male-female, 65-piece minimum) | 1 | Connecting everything. Pre-cut sets are easier than cutting your own. | $10 | Any vendor |
| **PTT button** (momentary, panel-mount, 30 mm preferred) | 1 | The "push to talk" button. | $5 | Adafruit, AliExpress |
| **Speaker for CH358** (8 Ω, ½–1 W) | 1 | Driven by the CH358 output. | $3 | Adafruit #1313 or similar |
| **Sound files for CH358** | 10 | Generated locally by `python tools/generate_sfx.py`. | free | self |
| **TF (microSD) card, ≤ 1 GB if module is restricted, otherwise any** | 1 | Holds the 10 WAVs for the CH358. | $5 | Any vendor |

**Estimated additional spend if procuring everything fresh:** **~$50.**
(Most of this is the breadboards + jumper kit + the PTT button; the
chips themselves are cents.)

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

---

## 3. Optional / future

| Part | Use | Status |
|---|---|---|
| **Arduino GIGA R1 WiFi**              | Host for the GIGA Display Shield (touch scenario-selector UI). | Procure if/when the touch UI path is desired; ~$80. |
| **Arduino GIGA Display Shield (ASX00039)** | Already in inventory; needs the R1 host. | In inventory, deferred. |
| **Mounting panel** (foam-core, plywood, or 3D-printed front plate) | Permanent housing per Chapter 13. | DIY; cost varies. |
| **Label maker or printable decals**   | Labelling switches and LEDs per scenario. | $20 for a Brother PT-D210 + tape, or free if hand-labelled. |
| **Soldering iron + protoboard**       | If the builder wants to migrate from breadboard to a permanent build. | Out of scope for the manual itself; pointer in Appendix D. |
| **Edge Impulse account**              | Train custom Nicla wake-word + keyword models. | Free tier sufficient; pointer in Appendix D. |
| **Second CH358 module**               | Per-scenario SFX banks instead of one universal bank. | Deferred — universal SFX bank is the design choice for now. |
| **MCP23017 breakout board (Adafruit #5346)** | Same chip but easier to wire (no DIP-on-breadboard fiddling). | Substitute for the bare chip if preferred — ~$8 vs ~$3. |
| **Anti-static wrist strap**           | Strictly safer chip handling. | $5; manual treats it as optional but recommended. |

---

## 4. Total cost (all-in, from a hypothetical zero-inventory start)

| Bucket | Cost |
|---|---|
| Pi 5 + 27 W PSU + 2 TB SSD                | ~$130 |
| Yahboom mic/speaker                        | ~$30  |
| C920 webcam                                | ~$70  |
| Metro RP2040                               | ~$15  |
| Arduino Nicla Voice                        | ~$80  |
| Inland PIR                                 | ~$5   |
| 1602 LCD with I²C backpack                 | ~$8   |
| Adafruit #938 OLED                         | ~$18  |
| STEMMA QT 128×64 OLED                      | ~$18  |
| CH358D-TF-1G                               | ~$10  |
| MT-301R4P-P                                | ~$30  |
| 10 toggle switches                         | ~$15  |
| 50 LEDs                                    | ~$10  |
| Chips + transistors + resistors + breadboards + jumpers + PTT button + speaker (Section 2) | ~$50  |
| **Total estimated cost**                   | **~$489** |

The user already has everything in Section 1, so realistic additional
spend is **~$50** (Section 2 only).

---

## 5. Notes for the manual author

- **Photograph every part on a labelled tray** before Chapter 1 is
  written. A photo with every part in inventory clearly labelled is the
  single most useful illustration in the entire manual.
- **Order ahead.** Section 2 parts (~$50) should be ordered before the
  bench writing begins. The wait kills momentum.
- **Buy 2× of the small consumables** (resistors, jumpers, LEDs). You
  *will* burn one out or lose one under the desk. Manual should
  acknowledge this normality.
