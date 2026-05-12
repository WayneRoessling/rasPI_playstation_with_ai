# Spaceship Cockpit — Changelog

All changes to `narrative.md` (and emitted YAML) are logged here in
reverse-chronological order. OLENT amendment discipline: every change
to the narrative source-of-truth gets a stanza, even small ones.

## v1 — 2026-05-12 — Initial authoring (Drop 6)

- First authored civilian/exploration vessel scenario.
- 10 named switch labels (Inertial Dampeners … Airlock) matching a
  small ship's bridge auxiliary panel.
- Persona: ship's computer, voice = Amy, calm and warm.
- Three scenario-specific tools added on top of the generic set:
  `engage_warp_drive` (arm-gated, requires S6+S7), `scan_sector`
  (not arm-gated), `vent_airlock` (arm-gated, requires S10).
- Wake-word allowlist: `computer`, `captain`.
- Intent allowlist: `status`, `arm`, `disarm`, `help`.
- Hardware modules referenced: RP2040 Metro, sim panel, CH358 sound,
  1602 LCD, OLED B, OLED MASTER.
- Acceptance cues described for both nominal (warp engage) and
  arm-gated refusal (warp without coils) paths.
