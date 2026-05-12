---
id: spaceship_cockpit
title: Spaceship Cockpit
version: 1
status: authored
voice: amy
persona_prompt: |
  You are the ship's computer aboard a civilian deep-space exploration
  vessel. You address the operator as "Captain" and refer to the panel as
  "the console". Your register is calm, helpful, slightly warm — think
  ship's-AI courtesy rather than mission-control terseness. Default to
  action: when the captain asks for something a tool covers, do it and
  give a one-line confirmation. Use ship terms naturally — "aft",
  "forward", "starboard", "warp factor", "impulse", "scan returns",
  "dampeners nominal". You are never theatrical and never anxious; if a
  destructive tool is refused by the safety key you say so once and stop.
  Round numbers; speak in two sentences or less.
switch_labels:
  - "Inertial Dampeners"
  - "Life Support"
  - "Nav Computer"
  - "Tractor Beam"
  - "Shields"
  - "Warp Coil"
  - "Impulse"
  - "Sensors"
  - "Cargo Bay"
  - "Airlock"
wake_words:
  - "computer"
  - "captain"
intent_allowlist:
  - "status"
  - "arm"
  - "disarm"
  - "help"
tools_scenario:
  - id: engage_warp_drive
    description: |
      Engage the warp drive. Validates Warp Coil (S6) and Impulse (S7)
      are on; refuses with the missing list otherwise. Plays SFX-COMMS,
      then SFX-TICK x 5 while lighting LEDs 11-15 (warp ramp), then
      SFX-STATUS at warp factor lock. Arm-gated.
    requires_arm: true
    parameters: {}
  - id: scan_sector
    description: |
      Sweep local sensors. Plays SFX-COMMS, writes "SECTOR SCAN" on
      LCD line 1 and a contact summary on line 2, and renders the
      contact list on OLED B. Not arm-gated.
    requires_arm: false
    parameters: {}
  - id: vent_airlock
    description: |
      Vent the starboard airlock. Requires Airlock (S10) toggle on.
      Plays SFX-ALARM, lights LEDs 31-40 (hazard band), renders
      "AIRLOCK VENT" alert on OLED B. Arm-gated.
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

# Spaceship Cockpit

## 1. World

A civilian-registered deep-space exploration vessel, three weeks out of
port on a routine sector survey. The captain is solo on the bridge; the
ship's computer is patient, gentle, omnipresent. There is no enemy and
no emergency by default — the rhythm is quiet maintenance, occasional
scans, the long boredom of interstellar transit.

The console in front of the captain is the cockpit auxiliary panel: ten
toggle switches for the major shipboard systems, an MT-301 isolator key
that gates the destructive tools, an LCD for system readouts, and the
two OLEDs for status and alerts. The bridge's main displays are
elsewhere; this panel is the captain's hand-on-controls quick-action
surface.

## 2. Console layout

Ten silver toggle switches, labeled left to right:

1. **Inertial Dampeners** — mass-effect compensators. Almost always on
   in flight; if off, the ship "feels" every acceleration. LED 1 mirror.
2. **Life Support** — atmosphere, thermal, scrubbers. Always on. LED 2.
3. **Nav Computer** — navigation solver, including warp-routing. Must
   be on for any warp engagement. LED 3.
4. **Tractor Beam** — short-range manipulator beam. Off by default;
   used for cargo retrieval and emergency rescue. LED 4.
5. **Shields** — deflector shielding against micrometeorites and
   debris. On during transit. LED 5.
6. **Warp Coil** — primary FTL drive. Required for `engage_warp_drive`.
   LED 6.
7. **Impulse** — sub-light propulsion. Required for `engage_warp_drive`
   (used for the pre-warp burn). LED 7.
8. **Sensors** — long-range sensor array. Needed for `scan_sector`. LED 8.
9. **Cargo Bay** — main cargo bay environmental seal. LED 9.
10. **Airlock** — starboard airlock outer-door safety. Must be on to
    permit `vent_airlock`. LED 10.

The 1602 LCD sits above the switches. Default content during cruise:

```
VEL  WARP 0.0
HDG  283.4    OK
```

OLED B is the right-hand status panel — used for scan returns,
navigation summaries, and alerts.

The OLED MASTER (top center) shows the always-on status block:
`scenario: SHIP`, `arm: SAFE/ARMED`, `health: GO/NOGO`.

LED 11–20 are sequence indicators (used by the warp-engage ramp). LEDs
21–30 are spare for this scenario. LEDs 31–40 are the hazard band, lit
for `vent_airlock`. LEDs 41–50 are unused.

## 3. Persona

The ship's computer's voice is **Amy** — clear, neutral, English. The
LLM speaks like an unflappable assistant: a single line of confirmation
when an action is taken, a single line of explanation when one is
refused. The voice does not narrate; it informs.

When asked "how are you", the computer briefly notes ship health, not
its own. "All systems nominal, Captain." When asked something it does
not know, it says so — "No contacts on scan." — and stops.

## 4. Wake & intent

The Nicla Voice keyword set is the universal ten. For this scenario the
wake words that matter are `computer` and `captain`. The intent
allowlist is the small set of generic intents — `status`, `arm`,
`disarm`, `help` — since most useful actions on a ship are too varied
to fit a fixed keyword.

## 5. Scenario-specific tools

Three tools on top of the generic set:

- **`engage_warp_drive`** — arm-gated. Validates S6 Warp Coil and
  S7 Impulse are on; otherwise refuses with the missing list. On
  success: plays SFX-COMMS, then SFX-TICK five times at 1 s intervals
  while lighting LEDs 11–15 in sequence (the warp-ramp), writes
  `ENGAGING WARP` on LCD line 1 and `WARP n.n` on line 2 each tick,
  then plays SFX-STATUS at warp lock and writes `WARP ACTIVE`.
- **`scan_sector`** — not arm-gated. Plays SFX-COMMS, writes
  `SECTOR SCAN` on LCD line 1 and a one-line contact summary on line
  2, and renders a 6-line contact list on OLED B (`text` layout).
  The contact list is procedurally chosen from a short bank of plausible
  exploration findings (e.g. "Asteroid cluster bearing 042", "Comet
  C/2278 inbound", "Long-range static, ambient").
- **`vent_airlock`** — arm-gated. Requires S10 Airlock toggle on;
  otherwise refuses. On success: plays SFX-ALARM, lights LEDs 31–40,
  renders an `ALERT: VENT` block on OLED B.

## 6. Acceptance cues

A "good" cockpit turn:

1. Captain says "engage warp factor 5".
2. Computer checks S6 and S7, plays SFX-COMMS, lights LEDs 11–15
   step-by-step over five seconds, writes `WARP n.n` on the LCD each
   step, finishes with SFX-STATUS and `WARP ACTIVE` on the LCD.
3. Voice reply: "Warp engaged, Captain. Hold for sublight on arrival."

A refused turn — warp without coils:

1. Captain says "go to warp".
2. Computer attempts `engage_warp_drive`; runtime returns `refused:
   warp checklist incomplete: Warp Coil`.
3. Voice reply: "Negative, Captain. Warp Coil is offline."

## 7. Open questions

- **Music bed.** A low-volume bridge ambience loop could play through
  the Pi speaker during cruise. Deferred — Drop 6.
- **Scan content.** Currently procedural from a small bank; a future
  iteration could pull from a richer narrative bank under
  `narratives/scenarios/spaceship_cockpit/scan_returns/`.

## 8. References

- `overlay/canonical/sfx_bank.yaml`
- `overlay/canonical/switches.yaml`
- `overlay/canonical/wake_words.yaml`
- `overlay/docs/HAL_PROTOCOL.md`
