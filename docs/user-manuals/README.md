# User Manuals

This folder holds the **hardware build manual** for the mini-ai system —
a step-by-step guide a high-school-aged builder can follow without prior
electronics experience.

## How to read it

Read the chapters in order. Each one assumes you've finished the previous
chapter and that the bench is in the state the previous checkpoint
described.

| # | Title | Status |
|---|---|---|
| 00 | [Welcome & Safety](00_welcome_and_safety.md) | **shipped (Drop 3)** |
| 01 | [What You Already Have](01_what_you_already_have.md) | **shipped (Drop 3)** |
| 02 | [The Big Picture of the Control Panel](02_big_picture_of_the_control_panel.md) | **shipped (Drop 3)** |
| 03 | [Setting Up Your Workspace](03_setting_up_your_workspace.md) | **shipped (Drop 3)** |
| 04 | [Powering Things](04_powering_things.md) | **shipped (Drop 3)** |
| 05 | [First Test: the Metro RP2040 Alone](05_first_test_metro_rp2040.md) | stub — Drop 4 |
| 06 | [The Sound Module (CH358D)](06_sound_module_ch358d.md) | stub — Drop 4 |
| 07 | [Panel Display A: the 1602 LCD](07_panel_display_a_1602_lcd.md) | stub — Drop 4 |
| 08 | [Panel Display B + Master: Two OLEDs](08_panel_display_b_two_oleds.md) | stub — Drop 4 |
| 09 | [Toggle Switches & MCP23017](09_toggle_switches_mcp23017.md) | stub — Drop 4 |
| 10 | [LEDs & the 74HC595 Shift-Register Chain](10_leds_74hc595_shift_register_chain.md) | stub — Drop 4 |
| 11 | [PTT, PIR, and the MT-301 Key Switch](11_ptt_pir_mt301_key_switch.md) | stub — Drop 4 |
| 12 | [The Always-On Ear: Arduino Nicla Voice](12_always_on_ear_nicla_voice.md) | stub — Drop 4 |
| 13 | [Permanent Build: Soldering, Perfboard, Panel Mounting](13_permanent_build_soldering_perfboard_panel.md) | stub — Drop 4 |
| 14 | [First Real Run](14_first_real_run.md) | stub — Drop 4 |
| 15 | [Troubleshooting](15_troubleshooting.md) | stub — Drop 4 |

## Appendices

| ID | Title | Status |
|---|---|---|
| A | [Bill of Materials](appendix_A_bill_of_materials.md) | **shipped (Drop 3)** |
| B | [Pinout Reference Card](appendix_B_pinout_reference_card.md) | **shipped** |
| C | [Glossary](appendix_C_glossary.md) | **shipped (Drop 3)** |
| D | [Going Further](appendix_D_going_further.md) | **shipped** |

## Planning documents

The plan that drives all chapter content is in [`plan/`](plan/):

- [`plan/BUILD_MANUAL_PLAN.md`](plan/BUILD_MANUAL_PLAN.md) — master plan:
  reader profile, 16-chapter outline, 9 locked-in decisions.
- [`plan/BILL_OF_MATERIALS.md`](plan/BILL_OF_MATERIALS.md) — every part
  the build needs, split by inventory / procure / optional.
- [`plan/STYLE_GUIDE.md`](plan/STYLE_GUIDE.md) — tone, callout boxes,
  jargon-introduction rules, diagram conventions.
- [`plan/DIAGRAM_LIST.md`](plan/DIAGRAM_LIST.md) — every illustration,
  photograph, and pin-out chart the manual will need (57 in total).

## Images

Diagrams and photographs referenced by the chapters (`images/D-0.1.png`,
etc.) are placeholders until they're produced separately, using Fritzing
for breadboard views, Inkscape for vector pinouts and analogies, and
GIMP for annotating in-house photographs. See
[`plan/DIAGRAM_LIST.md`](plan/DIAGRAM_LIST.md) for the full inventory
and production order.

**Shipped so far** (hand-coded SVG → PNG via headless Chromium; sources
in `source/`, rendered PNGs in `images/`):

| ID    | Diagram                              | Referenced in |
|-------|--------------------------------------|---------------|
| D-2.1 | Four-box architecture                | Ch 2          |
| D-3.1 | Breadboard internal connections      | Ch 3          |
| D-4.3 | Voltage = water-pressure analogy     | Ch 4          |

## Status

| Step | Status |
|---|---|
| 1. Outline + plan documents | done |
| 2. Review / approval | done |
| 3. **Chapters 0–4 + Appendices A and C (Drop 3)** | done |
| 4. **Appendix B (Pinout Reference Card) + diagrams D-2.1 / D-3.1 / D-4.3** | **done — this PR** |
| 5. Chapters 5–12 (per-module build at the bench) | pending — Drop 4 |
| 6. Chapters 13–15 (assemble + run + troubleshoot) | pending — Drop 4 |
| 7. **Appendix D (Going Further)** | **done — this PR** |
| 8. Production of the remaining diagrams and photographs | pending — separate workstream |

Start with [`00_welcome_and_safety.md`](00_welcome_and_safety.md).
