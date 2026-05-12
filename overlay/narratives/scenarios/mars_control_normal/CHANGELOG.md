# Mars Control Center — Normal Operations — Changelog

All changes to `narrative.md` (and emitted YAML) are logged here in
reverse-chronological order. OLENT amendment discipline: every change
to the narrative source-of-truth gets a stanza, even small ones.

## v1 — 2026-05-12 — Initial authoring (Drop 6)

- First authored Mars-normal scenario. Twin (same physical panel) of
  `mars_control_disaster`; same 10 switch labels, different persona
  and different tool set.
- 10 named switch labels (Habitat 1 … Surface Lock) matching the Mars
  Base ops console.
- Persona: Mars Control, voice = Lessac, calm/neighbourly.
- Three scenario-specific tools, none arm-gated:
  `daily_systems_check`, `query_resource`, `schedule_eva`.
- Wake-word allowlist: `computer`, `mission control`, `flight`.
- Intent allowlist: `status`, `arm`, `disarm`, `help`.
- Hardware modules: RP2040 Metro, sim panel, CH358 sound, 1602 LCD,
  OLED B, OLED MASTER.
- Acceptance cues described for both a tool-using ("run the morning
  check") and a parameterised tool turn ("how is water").
