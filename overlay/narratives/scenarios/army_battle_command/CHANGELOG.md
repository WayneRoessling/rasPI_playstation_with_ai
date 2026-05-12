# Army Battle Command Center — Changelog

All changes to `narrative.md` (and emitted YAML) are logged here in
reverse-chronological order. OLENT amendment discipline: every change
to the narrative source-of-truth gets a stanza, even small ones.

## v1 — 2026-05-12 — Initial authoring (Drop 6)

- First authored tactical / TOC scenario.
- 10 named switch labels (C2 Link … Stand-To) matching a battalion
  Tactical Operations Centre auxiliary console.
- Persona: battle-captain console operator, voice = Ryan, terse and
  decisive.
- Three scenario-specific tools — two arm-gated (heavy gate compared
  to other scenarios): `engage_target` (arm-gated + S3 + S4 required),
  `request_isr` (not arm-gated), `call_counter_battery` (arm-gated +
  S9 required).
- Wake-word allowlist: `computer`, `flight`.
- Intent allowlist: `abort`, `status`, `arm`, `disarm`, `help`.
- Hardware modules: RP2040 Metro, sim panel, CH358 sound, 1602 LCD,
  OLED B, OLED MASTER.
- Acceptance cues described for nominal (engage TGT-04) and two
  refusal paths (ROE off, key SAFE).
