---
id: space_command_launch
title: Space Command — Launch Control Center
version: 1
status: authored
voice: ryan
persona_prompt: |
  You are Mission Control at U.S. Space Command, Launch Control. You speak
  with calm, clipped Mission-Control cadence — short callouts, no filler,
  always status-first. Refer to the user as "Flight" or "Operator" and to
  the panel as "the console". Default to action over chatter: when a tool
  call satisfies a request, take it and report briefly. Use Mission-Control
  phrasing — "go", "no-go", "stand by", "copy", "roger", "we are committed",
  "T-minus", "lift-off" — when natural, but never theatrical. If the safety
  key is in SAFE you may run preflight checks, but ignition-class commands
  are arm-gated; relay the deny once and stop retrying. Round numbers; never
  apologize.
switch_labels:
  - "Ignition Arm"
  - "Boost Stage"
  - "Telemetry"
  - "Range Safety"
  - "Main Bus A"
  - "Main Bus B"
  - "Comms"
  - "Beacon"
  - "Hold"
  - "Abort"
wake_words:
  - "computer"
  - "mission control"
  - "flight"
intent_allowlist:
  - "launch"
  - "abort"
  - "status"
  - "arm"
  - "disarm"
  - "help"
tools_scenario:
  - id: initiate_launch_sequence
    description: |
      Begin the automated launch countdown. Plays a 10-second tick sequence
      on SFX-TICK, lights LED 1–10 sequentially, then plays SFX-STATUS at
      T-0. Arm-gated.
    requires_arm: true
    parameters: {}
  - id: hold_countdown
    description: |
      Halt an in-progress countdown. Clears tick sequence, lights LED
      "Hold" (S9), plays SFX-CAUTION. Not arm-gated.
    requires_arm: false
    parameters: {}
  - id: range_safety_destruct
    description: |
      Issue range-safety destruct command (simulation only — this scenario
      runs against the panel; no real vehicle is harmed). Lights LEDs 30–50,
      plays SFX-ALARM, renders BREACH on OLED B. Arm-gated.
    requires_arm: true
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

# Space Command — Launch Control Center

## 1. World

This is a U.S. Space Command launch facility somewhere on the Florida
coast, an hour before window. A booster sits on Pad 39B; payload is a
classified national-security spacecraft. The console in front of you is
the operator's tabletop — not the LCC main floor, but the
launch-conductor's auxiliary console: it carries every cue you need to
participate in the countdown without owning the final go/no-go.

The atmosphere is professional, focused, slightly bored — the bored
focus of a team that has done this fifty times. There is no
dramatization. Cues are clipped. When something is wrong, it is named
and worked, not exclaimed over.

## 2. Console layout

Ten silver toggle switches across the front edge, labeled left to right:

1. **Ignition Arm** — master enable for the ignition tool. Wired in
   software through the MT-301 safety key (toggle is necessary but not
   sufficient: the physical key must also be in ARM).
2. **Boost Stage** — staging telemetry enable. Lighting LED 2 confirms
   booster sensors are in the loop.
3. **Telemetry** — main downlink. Lights LED 3 and starts the periodic
   COMMS chirp on SFX slot 7.
4. **Range Safety** — destruct-link armed. Toggle plus arm-key both
   required to enable `range_safety_destruct`.
5. **Main Bus A** — primary power. Mirror LED 5.
6. **Main Bus B** — backup power. Mirror LED 6.
7. **Comms** — open the comm loop to the LCC. Lights LED 7, plays COMMS
   chirp once.
8. **Beacon** — vehicle beacon. Lights LED 8 and pulses LED 8 during
   active flight.
9. **Hold** — declare a hold. Lights LED 9 red, plays CAUTION. Inhibits
   the launch countdown tool until cleared.
10. **Abort** — request abort. Lights LEDs 1–10 in alternating pattern,
    plays ALARM. Does **not** itself destruct — that is Range Safety.

The 1602 LCD sits above the switches. Default content during prelaunch:

```
ALT  GROUND     T-?:??
FUEL ----       RDY OK
```

OLED B is the right-hand status panel. Default `status` layout with
`scenario: SPACECMD`, `arm: SAFE/ARMED`, `health: GO/NOGO`.

The OLED MASTER (top center, next to the MT-301 key) shows the same
status block always — it is the global console state-of-truth.

The 50 LEDs are bottom rail: 1–10 are switch mirrors; 11–20 are
sequence-progress LEDs (light one per second during countdown); 21–30
are unused on this scenario; 31–50 are the "destruct annunciator"
pattern (all lit + flashing on Range Safety).

## 3. Persona

Mission Control's voice is **Ryan** — a clear American male voice. The
LLM speaks in Mission-Control register: brief, status-first, no
apologies, no narration. When asked the time-to-launch, say "T minus
X". When asked status, give a single line: "Console nominal" or "Hold
at Telemetry — LED 9 lit". Never speak more than two sentences. The
panel is doing the visible work; the voice merely confirms.

When a destructive tool is refused for safety-key reasons, the deny
is reported once: "Negative — safety key SAFE, ignition inhibit." No
retry, no plea.

## 4. Wake & intent

The Nicla Voice keyword set is the default ten — see
`canonical/wake_words.yaml`. For this scenario the wake words that
matter most are `computer`, `mission control`, and `flight`. Direct-
intent keywords (no Whisper round-trip) that act locally:

- `launch` — fires `initiate_launch_sequence` if armed, else plays DENY.
- `abort` — same as the Abort switch.
- `status` — voice-reads the OLED MASTER block.
- `arm` / `disarm` — narrate the key position currently observed (cannot
  actually rotate the physical key; the operator must do that).
- `help` — recites the wake-word list.

The intent allowlist above is enforced by the scenario module — any
other keyword from the bank is dropped silently for this scenario.

## 5. Scenario-specific tools

Three tools are added on top of the generic set:

- **`initiate_launch_sequence`** — arm-gated. Validates Boost Stage
  (S2), Telemetry (S3), Main Bus A (S5), and Comms (S7) are all on;
  otherwise returns `refused: launch checklist incomplete: <list>`.
  On success: plays SFX-COMMS once, plays SFX-TICK 10 times at 1 s
  intervals, lights LEDs 11..20 in turn, writes `T-10..T-0` to LCD
  line 2, then plays SFX-STATUS at T-0 and writes `LIFTOFF` on LCD
  line 1.
- **`hold_countdown`** — not arm-gated. Lights LED 9, plays
  SFX-CAUTION, writes `HOLD` on LCD line 1.
- **`range_safety_destruct`** — arm-gated. Requires S4 (Range Safety)
  toggle on. Otherwise returns `refused: range safety toggle is open`.
  On success: lights LEDs 31–50, plays SFX-ALARM, renders BREACH on
  OLED B.

## 6. Acceptance cues

A "good" launch-control turn:

1. Operator says "begin launch sequence checks".
2. Mission Control checks state, writes `PRELAUNCH OK` to LCD line 1
   and `KEY ${ARM_STATE}` to line 2, lights LEDs 1–7 to indicate the
   first seven switches' nominal positions, plays an ACK.
3. Voice reply: one line — "Console go for launch checks. Awaiting
   ignition arm." or similar.

A "bad" turn — destruct asked while key is SAFE:

1. Operator says "fire the destruct".
2. Runtime refuses (arm-gate), plays DENY.
3. Voice reply: one line — "Negative — safety key SAFE."

## 7. Open questions

- **Audio bed.** A scenario-specific intro stinger ("Space Command,
  Flight, on console") could play once at scenario load through the Pi
  speaker. Deferred — Drop 6.
- **Real-world fidelity.** Pad and vehicle naming is intentionally
  vague. We're not modeling a specific flight.
- **Co-located ground crew chatter.** A future enhancement could pipe
  a low-volume loop of ambient comms in the background. Deferred.

## 8. References

- `overlay/canonical/sfx_bank.yaml` — the 10 universal SFX.
- `overlay/canonical/switches.yaml` — switch labels for all scenarios.
- `overlay/canonical/wake_words.yaml` — Nicla keyword bank.
- `overlay/docs/HAL_PROTOCOL.md` — the wire format Mission Control
  speaks to the console.
