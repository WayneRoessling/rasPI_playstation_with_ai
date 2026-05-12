# Space Command — Launch Control Center — Changelog

All changes to `narrative.md` (and emitted YAML) are logged here in
reverse-chronological order. OLENT amendment discipline: every change
to the narrative source-of-truth gets a stanza, even small ones.

## v1 — 2026-05-11 — Initial authoring (Drop 3)

- First authored scenario for the mini-ai overlay subsystem.
- 10 named switch labels (Ignition Arm … Abort) matching the
  Mission-Control launch-conductor's auxiliary console.
- Persona: Mission Control / Launch Control, voice = Ryan, clipped
  status-first cadence.
- Three scenario-specific tools added on top of the generic set:
  `initiate_launch_sequence` (arm-gated), `hold_countdown`,
  `range_safety_destruct` (arm-gated + S4 required).
- Wake-word allowlist: `computer`, `mission control`, `flight`.
- Intent allowlist: `launch`, `abort`, `status`, `arm`, `disarm`,
  `help`.
- Hardware modules referenced: RP2040 Metro, sim panel, CH358 sound,
  1602 LCD, OLED B, OLED MASTER.
- Acceptance cues described for both nominal and arm-gated paths.
