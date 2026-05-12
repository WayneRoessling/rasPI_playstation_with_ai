# Mars Control Center — Disaster Response — Changelog

All changes to `narrative.md` (and emitted YAML) are logged here in
reverse-chronological order. OLENT amendment discipline: every change
to the narrative source-of-truth gets a stanza, even small ones.

## v1 — 2026-05-12 — Initial authoring (Drop 6)

- First authored Mars-disaster scenario. Twin of `mars_control_normal`
  — same 10 switch labels, same physical panel, sharpened persona,
  destructive tool set.
- 10 named switch labels (identical to `mars_control_normal`): Habitat
  1 … Surface Lock.
- Persona: Mars Control under crisis, voice = Lessac (same as normal —
  one Control voice, different cadence).
- Three scenario-specific tools: `evacuate_sector` (arm-gated),
  `seal_habitat` (not arm-gated — defensive action), `broadcast_mayday`
  (not arm-gated).
- Wake-word allowlist: `computer`, `mission control`, `flight`.
- Intent allowlist: `abort`, `status`, `arm`, `disarm`, `help`. Adds
  `abort` over the normal scenario for the verbal short-circuit.
- Hardware modules: RP2040 Metro, sim panel, CH358 sound, 1602 LCD,
  OLED B, OLED MASTER.
- Acceptance cues described for nominal (hab2 breach response) and
  arm-gated refusal (evacuate without key) paths.
- Explicit cross-reference to `mars_control_normal/narrative.md` in
  §8 to make the twin-scenario relationship clear to readers.
