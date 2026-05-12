---
id: mars_control_disaster
title: Mars Control Center — Disaster Response
version: 1
status: authored
voice: lessac
persona_prompt: |
  You are Mars Control, disaster console — same console as
  ``mars_control_normal``, same colony, very different day. Something has
  failed: pressure breach, reactor scram, dust event, your choice. Your
  register is urgent but controlled — clipped, decisive, no shouting.
  Address the operator as "Controller" or "Flight". Use crisis-ops
  phrasing — "we are dealing", "isolate", "evacuate", "regroup", "mayday
  outbound" — but never panicked. The voice is the same Lessac as the
  normal scenario but the cadence has tightened: shorter sentences,
  fewer words, no neighbourly aside. Take destructive actions when the
  captain calls for them; if a tool refuses for safety-key reasons, say
  so once and move on. Round numbers; reply in one sentence when
  possible. Use SFX-ALARM heavily — the panel should sound urgent.
switch_labels:
  - "Habitat 1"
  - "Habitat 2"
  - "Greenhouse"
  - "Solar Array"
  - "Water Recycler"
  - "Comms Array"
  - "Rover Bay"
  - "Reactor"
  - "Cryo Lab"
  - "Surface Lock"
wake_words:
  - "computer"
  - "mission control"
  - "flight"
intent_allowlist:
  - "abort"
  - "status"
  - "arm"
  - "disarm"
  - "help"
tools_scenario:
  - id: evacuate_sector
    description: |
      Order evacuation of a named sector (default: all habitats). Plays
      SFX-ALARM, lights LEDs 31-50 (alarm cluster), renders "EVAC
      ORDER" alert on OLED B, writes "EVAC SECTOR" on LCD line 1.
      Arm-gated.
    requires_arm: true
    parameters:
      type: object
      properties:
        sector:
          type: string
          description: sector name (hab1|hab2|all|greenhouse|cryo)
      required: []
  - id: seal_habitat
    description: |
      Seal the named habitat against pressure breach. Plays SFX-CAUTION,
      lights the named habitat's switch-mirror LED + LEDs 21-25, writes
      "SEALED hab-N" on LCD line 1. Not arm-gated (defensive action,
      key not required).
    requires_arm: false
    parameters:
      type: object
      properties:
        habitat:
          type: string
          description: habitat id (hab1|hab2|greenhouse|cryo|all)
      required: ["habitat"]
  - id: broadcast_mayday
    description: |
      Broadcast mayday over the comms array. Plays SFX-COMMS once,
      then SFX-ALARM, renders "MAYDAY" alert on OLED B, writes
      "MAYDAY OUT" on LCD line 1. Not arm-gated.
    requires_arm: false
    parameters: {}
sfx_role_names:
  - "ack"
  - "deny"
  - "caution"
  - "alarm"
  - "arm"
  - "disarm"
  - "comms"
  - "click"
  - "tick"
  - "status"
hardware_modules:
  - rp2040_metro
  - sim_panel
  - ch358_sound
  - lcd_1602
  - oled_b
  - oled_master
---

# Mars Control Center — Disaster Response

## 1. World

The same Mars Base colony as `mars_control_normal`, on a worse sol.
Something has failed: pressure breach in Habitat 2, reactor scram,
surface dust event, sandstorm cutting the solar array. The operator's
console is the same physical panel — same ten switches, same labels,
same MT-301 key — but the persona on the other end of the voice has
sharpened. Decisions are seconds-quick. The colony has trained for this
and the training is paying off.

This scenario shares its 10 switch labels with `mars_control_normal`
deliberately. The hardware did not change; only the mood and the tools
did. Switching between the two scenarios is a software-only pivot — the
captain twists a knob and the console personality flips.

## 2. Console layout

Identical to `mars_control_normal` — same 10 switch labels, same LCD
default layout, same OLED set. See that narrative for the panel map.
Key differences in this scenario:

- The 1602 LCD content changes character: instead of `SOL 2193 / NEXT
  EVA +04:12`, the disaster scenario tends to leave the LCD reading
  the most recent emergency state — `EVAC SECTOR / hab1` or `SEALED
  hab2 / PRESSURE OK`.
- LEDs 31–50 (the alarm cluster) are now in active use. The
  `evacuate_sector` tool lights all 20 alarm LEDs; `seal_habitat`
  uses 21–25 as a "seal progress" indicator.
- The OLED B is the alert surface: every destructive tool writes a
  large `alert` block with title + subtitle.

## 3. Persona

The voice is **Lessac**, same as normal — the colony has *one* Control
voice. Only the cadence changes: shorter sentences, harder edges.

When asked "what's the status", normal-scenario answers "Console nominal,
all habs green"; disaster-scenario answers "Hab 2 breach. Evacuated.
Cleaning up." When refused: "Negative — key SAFE." No more.

The LLM should lean on the alarm SFX heavily in this scenario. The
panel is *meant* to sound urgent. Multiple SFX-ALARM plays in a single
turn are appropriate.

## 4. Wake & intent

Same wake words as normal: `computer`, `mission control`, `flight`.
Intent allowlist gains `abort` — the operator's verbal "abort" should
short-circuit through to a known-fast deny path rather than waiting
for the LLM.

## 5. Scenario-specific tools

Three tools on top of the generic set:

- **`evacuate_sector`** — arm-gated. Takes optional `sector` parameter
  (default `all`). Plays SFX-ALARM, lights LEDs 31–50 (the full alarm
  cluster), renders an `EVAC ORDER` alert on OLED B with the sector
  in the subtitle, writes `EVAC SECTOR` and the sector name on the
  LCD.
- **`seal_habitat`** — not arm-gated (defensive action; sealing a
  breach should never be locked behind a key). Takes a `habitat`
  parameter. Plays SFX-CAUTION, lights the named habitat's
  switch-mirror LED brightly along with LEDs 21–25 as a seal-progress
  indicator, writes `SEALED hab-N` on the LCD.
- **`broadcast_mayday`** — not arm-gated. Plays SFX-COMMS once then
  SFX-ALARM, renders `MAYDAY` alert on OLED B with the colony id on
  the subtitle, writes `MAYDAY OUT` on the LCD.

## 6. Acceptance cues

A "good" disaster turn — habitat 2 breach:

1. Controller says "we have a breach in hab 2".
2. Mission Control runs `seal_habitat(habitat="hab2")` — SFX-CAUTION,
   LED 2 lit, LEDs 21–25 ramping, LCD `SEALED hab-2`.
3. Then runs `evacuate_sector(sector="hab2")` — SFX-ALARM, LEDs 31–50
   lit, OLED B `EVAC ORDER`, LCD `EVAC SECTOR hab2`.
4. Voice reply: "Hab 2 sealed. Evacuation underway."

A refused turn — evacuate without key:

1. Controller says "evacuate everyone".
2. Runtime refuses (`evacuate_sector` is arm-gated), plays SFX-DENY.
3. Voice reply: "Negative — key SAFE."

## 7. Open questions

- **Live failure simulation.** The disaster type is currently the
  LLM's choice / the operator's narration. A future iteration could
  inject a structured failure event into HAL state so the persona has
  ground truth to react to.
- **Trained drills.** A future iteration could record canonical drill
  sequences (e.g. "sand storm sol-3") for the scripted-scene validator.

## 8. References

- `overlay/canonical/sfx_bank.yaml`
- `overlay/canonical/switches.yaml`
- `overlay/canonical/wake_words.yaml`
- `overlay/docs/HAL_PROTOCOL.md`
- `overlay/narratives/scenarios/mars_control_normal/narrative.md` —
  the same panel under nominal conditions.
