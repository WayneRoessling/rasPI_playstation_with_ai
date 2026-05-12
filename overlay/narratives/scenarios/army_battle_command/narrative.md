---
id: army_battle_command
title: Army Battle Command Center
version: 1
status: authored
voice: ryan
persona_prompt: |
  You are the battle-captain console operator in an Army battalion
  Tactical Operations Centre (TOC). Your register is terse, decisive,
  and military-flat — short callouts, no filler, status-first. Address
  the operator as "TOC", "Six", or "Battle". Refer to the panel as "the
  board". Default hard to action: when a tool covers the request, take
  it and report briefly. Use TOC phrasing — "copy", "wilco", "negative",
  "out", "weapons free", "ROE active", "send it", "stand by" — but never
  Hollywood. Most destructive tools are arm-gated; if refused, relay the
  deny one time and stop. Round all numbers; keep replies to one
  sentence. The tone is calm, professional, decisive, never agitated.
switch_labels:
  - "C2 Link"
  - "ISR Feed"
  - "Weapons Free"
  - "ROE Active"
  - "EMCON"
  - "Comms Sec"
  - "Drone Net"
  - "AAA Battery"
  - "Counter-Battery"
  - "Stand-To"
wake_words:
  - "computer"
  - "flight"
intent_allowlist:
  - "abort"
  - "status"
  - "arm"
  - "disarm"
  - "help"
tools_scenario:
  - id: engage_target
    description: |
      Engage a tactical target. Validates Weapons Free (S3) and ROE
      Active (S4) are on; refuses with the missing list otherwise.
      Plays SFX-ALARM, lights LEDs 31-40 (fires band), writes
      "ENGAGE" on LCD line 1 and the target id on line 2. Arm-gated.
    requires_arm: true
    parameters:
      type: object
      properties:
        target_id:
          type: string
          description: target identifier (e.g. TGT-04, BMP-02)
      required: ["target_id"]
  - id: request_isr
    description: |
      Request ISR (intelligence, surveillance, reconnaissance) overpass.
      Plays SFX-COMMS, writes "ISR REQ" on LCD line 1, renders the
      overpass details on OLED B. Not arm-gated.
    requires_arm: false
    parameters:
      type: object
      properties:
        bearing:
          type: string
          description: compass bearing for the overpass
      required: []
  - id: call_counter_battery
    description: |
      Call counter-battery fire on a hostile firing position. Requires
      Counter-Battery (S9) toggle on. Plays SFX-ALARM, lights LEDs
      41-50 (counter-battery band), writes "COUNTER-BTRY" on LCD line
      1 and the grid on line 2, renders alert on OLED B. Arm-gated.
    requires_arm: true
    parameters:
      type: object
      properties:
        grid:
          type: string
          description: target grid reference
      required: ["grid"]
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

# Army Battle Command Center

## 1. World

A battalion Tactical Operations Centre (TOC) somewhere forward. Mid-
intensity conflict; the tempo is high but the tone is professional. The
battle-captain runs a continuous loop of: monitor ISR, allocate fires,
control airspace, deconflict, brief Six. The console in front of the
captain is the auxiliary fires-and-comms board — not the main shared
displays, but the captain's quick-action surface.

This is the most arm-gated of the six scenarios. Lethal effects require
the MT-301 key in ARM by default; defensive and informational tools do
not.

## 2. Console layout

Ten silver toggle switches across the front edge, labeled left to right:

1. **C2 Link** — uplink to brigade. Always on. LED 1.
2. **ISR Feed** — feed from organic drones / divisional assets. LED 2.
3. **Weapons Free** — weapons authorization. Required for `engage_target`.
4. **ROE Active** — rules of engagement currently in force. Required
   for `engage_target`.
5. **EMCON** — emission control. If on, comms-emitting tools should
   be used sparingly (this scenario doesn't enforce — future drop).
6. **Comms Sec** — comms security state. Always on in TOC. LED 6.
7. **Drone Net** — drone network enable. Needed by `request_isr`
   implicitly; this scenario doesn't validate (future drop).
8. **AAA Battery** — anti-aircraft battery control. LED 8.
9. **Counter-Battery** — counter-battery fire authorization. Required
   for `call_counter_battery`.
10. **Stand-To** — full stand-to alert state. LED 10.

The 1602 LCD sits above the switches. Default content:

```
DTG  121130Z*
BLUE GRN  RED YEL
```

OLED B is the alert / ISR detail panel.

The OLED MASTER (top center) shows `scenario: ARMY TOC`, `arm:
SAFE/ARMED`, `health: GO/NOGO`.

LEDs 11–20 are unused on this scenario. LEDs 21–30 are spare. LEDs
31–40 are the fires band (lit on `engage_target`). LEDs 41–50 are the
counter-battery band (lit on `call_counter_battery`).

## 3. Persona

The voice is **Ryan** — clear American male, the same voice the Space
Command scenario uses but in a different register. The LLM speaks in
TOC-callout cadence: never narrate, never theatrical, always
status-first.

When asked status: "Board green, ROE active." Never more. When asked to
engage without authorization: "Negative — weapons not free." When a
tool refuses for arm-gate: "Negative — key SAFE." One sentence, no
retry.

## 4. Wake & intent

Wake words: `computer`, `flight` (Mission-Control-style address survives
into the TOC). Intent allowlist includes `abort` for the verbal
short-circuit on an in-progress engagement, plus the generic small set.

## 5. Scenario-specific tools

Three tools on top of the generic set:

- **`engage_target`** — arm-gated. Validates S3 Weapons Free and S4
  ROE Active are on; otherwise refuses with the missing list. Takes
  a `target_id` parameter. Plays SFX-ALARM, lights LEDs 31–40 (fires
  band), writes `ENGAGE` on LCD line 1 and the target id on line 2.
- **`request_isr`** — not arm-gated. Takes optional `bearing`
  parameter. Plays SFX-COMMS, writes `ISR REQ` on the LCD, renders
  the overpass details on OLED B (`text` layout).
- **`call_counter_battery`** — arm-gated. Requires S9 Counter-Battery
  toggle on; otherwise refuses. Takes a `grid` parameter. Plays
  SFX-ALARM, lights LEDs 41–50 (counter-battery band), writes
  `COUNTER-BTRY` and the grid on the LCD, renders an alert on OLED B.

## 6. Acceptance cues

A "good" battle turn:

1. TOC says "engage TGT-04".
2. Battle captain runs `engage_target(target_id="TGT-04")` — SFX-ALARM,
   LEDs 31–40 lit, LCD reads `ENGAGE / TGT-04`.
3. Voice reply: "Engaging TGT-04."

A refused turn — engage without ROE:

1. TOC says "engage TGT-04".
2. Runtime returns `refused: engagement checklist incomplete: ROE
   Active` (S4 is off).
3. Voice reply: "Negative — ROE not active."

A refused turn — engage with key SAFE:

1. TOC says "engage TGT-04".
2. Runtime refuses (arm-gated), plays SFX-DENY.
3. Voice reply: "Negative — key SAFE."

## 7. Open questions

- **EMCON enforcement.** Currently the EMCON switch is informational
  only. A future iteration could refuse `request_isr` and
  `broadcast_*` tools when S5 is on, and play SFX-DENY.
- **Live target/grid roster.** Currently free-text parameters. A
  future iteration could validate against a canonical target list.

## 8. References

- `overlay/canonical/sfx_bank.yaml`
- `overlay/canonical/switches.yaml`
- `overlay/canonical/wake_words.yaml`
- `overlay/docs/HAL_PROTOCOL.md`
