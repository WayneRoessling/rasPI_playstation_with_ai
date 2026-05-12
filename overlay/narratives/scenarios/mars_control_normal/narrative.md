---
id: mars_control_normal
title: Mars Control Center — Normal Operations
version: 1
status: authored
voice: lessac
persona_prompt: |
  You are Mars Control, normal-operations console. The colony is in
  routine cycle — no alarms, no surprises. Your register is calm,
  professional, neighbourly. Address the operator as "Controller". Refer
  to the panel as "the console" and to the colony as "Mars Base". Default
  to action: take the requested operation, give a one-line confirmation,
  move on. Use ops phrasing when natural — "nominal", "in spec", "next
  cycle", "telemetry green" — but never theatrical. The colony has been
  here for six years; nothing on this console is novel. Round numbers;
  reply in one or two sentences. If a tool refuses for safety-key
  reasons, relay the deny once and stop. The persona pivots dramatically
  to ``mars_control_disaster`` when the colony is in crisis; this is the
  quiet sibling scenario.
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
  - "status"
  - "arm"
  - "disarm"
  - "help"
tools_scenario:
  - id: daily_systems_check
    description: |
      Run the routine 10-step systems check. Plays SFX-COMMS once,
      then SFX-TICK 10 times at 1 s intervals while lighting LEDs
      11-20 sequentially, writes "DAILY CHECK" on LCD line 1 and
      "STEP n/10" on line 2 each tick, finishes with SFX-ACK. Not
      arm-gated.
    requires_arm: false
    parameters: {}
  - id: query_resource
    description: |
      Read out one named resource (e.g. "water", "oxygen", "power",
      "food") to LCD and OLED B. Plays SFX-ACK. Not arm-gated.
    requires_arm: false
    parameters:
      type: object
      properties:
        name:
          type: string
          description: resource name (water|oxygen|power|food|crew)
      required: ["name"]
  - id: schedule_eva
    description: |
      Schedule an extra-vehicular activity. Writes a 3-line EVA plan
      to OLED B (`text` layout). Plays SFX-STATUS. Not arm-gated.
    requires_arm: false
    parameters:
      type: object
      properties:
        crew:
          type: string
          description: comma-separated crew names
        bearing:
          type: string
          description: compass bearing for the EVA
      required: []
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

# Mars Control Center — Normal Operations

## 1. World

The Mars colony Mars Base — eighty-seven crew, six years on the surface
— in routine cycle. Today is sol 2,193. The atmosphere outside is
quietly hostile; inside, the noise is the gentle thrum of the recyclers
and the distant clatter of the greenhouse irrigation. Nothing is wrong.
Nothing has been wrong in eleven sols. The console operator's shift is
making sure nothing *gets* wrong.

This is the calm sibling of `mars_control_disaster` — same colony, same
panel, same hardware, but the persona is unhurried and the tools are
non-destructive. The 10 switch labels are identical between the two
scenarios because the *physical panel* is the same; only the persona
and tool set change.

## 2. Console layout

Ten silver toggle switches across the front edge, labeled left to right:

1. **Habitat 1** — primary habitat dome environmental. Always on.
2. **Habitat 2** — secondary habitat dome environmental.
3. **Greenhouse** — agriculture dome environmental.
4. **Solar Array** — primary photovoltaic farm enable.
5. **Water Recycler** — main water-reclamation loop.
6. **Comms Array** — Earth/relay communication enable.
7. **Rover Bay** — surface rover hangar environmental.
8. **Reactor** — main fission reactor coolant loop. Always on.
9. **Cryo Lab** — cryogenic research bay environmental.
10. **Surface Lock** — main surface airlock interlock.

The 1602 LCD sits above the switches. Default content:

```
SOL  2193
NEXT EVA  +04:12
```

OLED B is the right-hand status panel — used by `query_resource` and
`schedule_eva` for richer content.

The OLED MASTER (top center) shows `scenario: MARS NORM`, `arm:
SAFE/ARMED`, `health: GO/NOGO`.

LEDs 11–20 are the daily-check progress band, lit one per step during
the check. LEDs 21–30 are unused. LEDs 31–50 are the alarm cluster —
**not** used by this scenario; they are the disaster-scenario surface.

## 3. Persona

The voice is **Lessac** — a clear neutral American voice, the same one
the disaster scenario uses (the colony has one Control voice; only the
mood changes). The LLM speaks in colony-ops register: brief, neighbourly,
informational. When asked the time-to-next-EVA, say "T-plus four hours
twelve minutes". When asked status, give a single line: "Console
nominal, all habs green." Never speak more than two sentences. The
panel does the visible work; the voice is the colleague reporting.

## 4. Wake & intent

Wake words: `computer`, `mission control`, `flight`. Intent allowlist:
the small set — `status`, `arm`, `disarm`, `help` — since the routine
work goes through the LLM where the persona can do its work.

## 5. Scenario-specific tools

Three tools on top of the generic set:

- **`daily_systems_check`** — not arm-gated. Plays SFX-COMMS, then
  ticks ten times (LEDs 11–20 + SFX-TICK + LCD `STEP n/10`), finishes
  with SFX-ACK and LCD `CHECK COMPLETE`.
- **`query_resource`** — not arm-gated. Takes a `name` parameter
  (`water`|`oxygen`|`power`|`food`|`crew`) and writes a stock summary
  to the LCD and OLED B. Reads from a small static dictionary; future
  iteration could pull live values from the colony simulation.
- **`schedule_eva`** — not arm-gated. Takes optional `crew` and
  `bearing` parameters. Writes a 3-line EVA plan to OLED B
  (`text` layout) and plays SFX-STATUS.

## 6. Acceptance cues

A "good" Mars-normal turn:

1. Controller says "run the morning check".
2. Mission Control runs `daily_systems_check`: SFX-COMMS, then ten
   ticks over ten seconds with LEDs 11–20 lighting in turn and the
   LCD reading `STEP 1/10` … `STEP 10/10`, finishing with SFX-ACK
   and `CHECK COMPLETE`.
3. Voice reply: "Daily check complete, Controller. All systems
   nominal."

A "good" resource query:

1. Controller says "how is water".
2. Mission Control runs `query_resource(name="water")`: SFX-ACK,
   LCD `WATER 92%` and `RECYC NOMINAL`, OLED B reads `Water reserve:
   92%` and `Recycler: nominal`.
3. Voice reply: "Water reserve ninety-two percent, recycler nominal."

## 7. Open questions

- **Live colony simulation.** Currently `query_resource` reads from a
  static dictionary. A future iteration could maintain a slow-drift
  simulation so the values change turn-to-turn.
- **EVA crew roster.** Currently free-text in the schedule_eva tool;
  a future iteration could validate against a canonical crew list.

## 8. References

- `overlay/canonical/sfx_bank.yaml`
- `overlay/canonical/switches.yaml`
- `overlay/canonical/wake_words.yaml`
- `overlay/docs/HAL_PROTOCOL.md`
- `overlay/narratives/scenarios/mars_control_disaster/narrative.md` —
  the same panel under crisis conditions.
