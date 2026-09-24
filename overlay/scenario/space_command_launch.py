"""Space Command — Launch Control Center scenario.

The first real authored scenario (Drop 3). Built from the emitted YAML at
``overlay/narratives/scenarios/space_command_launch/_emitted/scenario.yaml``
so the narrative remains the single source of truth — running
``overlay/tools/emit_scenarios.py space_command_launch`` regenerates the
emitted YAML, and importing this module picks it up on the next
``ScenarioRuntime`` construction.

Three scenario-specific tools are added on top of the generic set:

* ``initiate_launch_sequence`` — arm-gated, validates the four mandatory
  prelaunch switches (S2 Boost Stage, S3 Telemetry, S5 Main Bus A,
  S7 Comms), then plays comms + 10×tick + status while lighting the
  countdown LEDs. The countdown runs in the background (see sequences.py).
* ``hold_countdown`` — not arm-gated; stops a running countdown and declares a hold.
* ``range_safety_destruct`` — arm-gated AND requires S4 Range Safety
  toggle on; simulated destruct cue.

Authored scenarios are not unit-tested at the Python level — they are
validated end-to-end by ``python -m overlay.scenario.demo --scenario
space_command_launch …`` against the simulator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .runtime import Scenario
from . import sequences
from .loader import build_from_emitted
from .tools import Tool




# ── Scenario-specific tool executors ─────────────────────────────────────


# Switches the prelaunch checklist requires (mapped to switch IDs 1..10).
#   S2 Boost Stage, S3 Telemetry, S5 Main Bus A, S7 Comms
PRELAUNCH_REQUIRED_SWITCHES: tuple[int, ...] = (2, 3, 5, 7)

# Switch labels for messages back to the LLM. Kept in sync with the
# emitted scenario YAML, but duplicated here so error messages don't
# require a YAML reload at dispatch time.
SWITCH_LABELS: dict[int, str] = {
    1: "Ignition Arm",
    2: "Boost Stage",
    3: "Telemetry",
    4: "Range Safety",
    5: "Main Bus A",
    6: "Main Bus B",
    7: "Comms",
    8: "Beacon",
    9: "Hold",
    10: "Abort",
}


def _exec_initiate_launch_sequence(hal, args: dict) -> str:
    """Run the prelaunch checklist, then a 10-second visible/audible countdown."""
    del args  # no parameters

    state = hal.state()
    switches = state.get("switches") or [0] * 10
    missing = [
        SWITCH_LABELS[i] for i in PRELAUNCH_REQUIRED_SWITCHES
        if not switches[i - 1]
    ]
    if missing:
        return f"refused: launch checklist incomplete: {', '.join(missing)}"

    # Comms open — single SFX-COMMS chirp
    hal.play_sfx(7)

    # Set initial LCD state
    hal.write_lcd(1, "COUNTDOWN ACTIVE")
    hal.write_lcd(2, "T-10")

    # The 10 s countdown runs in the background so the conversation (and a
    # hold_countdown) can continue while it plays out.
    sequences.start(hal, "launch countdown", _run_countdown)
    return ("ok: launch countdown started; T-10 now, liftoff in 10 seconds. "
            "Call hold_countdown to stop it.")


def _run_countdown(hal, cancelled) -> None:
    # Light LEDs 11..20 and write T-N to LCD, paced by 1 s ticks, one
    # SFX-TICK per second.
    for n in range(10, 0, -1):
        idx = 11 + (10 - n)             # 11..20
        hal.set_led(idx, on=True)
        hal.write_lcd(2, f"T-{n:02d}")
        hal.play_sfx(9)                 # SFX-TICK
        if cancelled.wait(1.0):
            return                      # hold — leave the panel where it stopped

    # T-0
    hal.write_lcd(1, "LIFTOFF")
    hal.write_lcd(2, "T-00")
    hal.play_sfx(10)                    # SFX-STATUS


def _exec_hold_countdown(hal, args: dict) -> str:
    """Declare a hold — stop any running countdown, caution, hold LED, HOLD on LCD."""
    del args
    stopped = sequences.cancel(hal)
    hal.set_led(9, on=True)             # Hold (S9 mirror)
    hal.play_sfx(3)                     # SFX-CAUTION
    hal.write_lcd(1, "HOLD")
    if stopped:
        return f"ok: hold declared; {stopped} stopped"
    return "ok: hold declared (no countdown was running)"


def _exec_range_safety_destruct(hal, args: dict) -> str:
    """Arm-gated AND requires S4 Range Safety toggle on."""
    del args
    state = hal.state()
    switches = state.get("switches") or [0] * 10
    if not switches[3]:                 # S4 index = 3
        return "refused: range safety toggle is open"
    # Light alarm cluster
    for led in range(31, 51):
        hal.set_led(led, on=True)
    hal.play_sfx(4)                     # SFX-ALARM
    hal.render_oled("B", "alert", {"title": "BREACH", "subtitle": "range safety destruct"})
    return "ok: range safety destruct issued"


INITIATE_LAUNCH = Tool(
    name="initiate_launch_sequence",
    description=(
        "Begin the automated launch countdown. Validates S2 Boost Stage, "
        "S3 Telemetry, S5 Main Bus A, S7 Comms are on; refuses with a "
        "list of missing switches otherwise. Plays comms chirp and starts a "
        "10-second countdown that runs in the background (LEDs 11-20, "
        "SFX-TICK, LCD T-N), ending with SFX-STATUS and LIFTOFF on the LCD. "
        "Returns as soon as the countdown starts. Arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_initiate_launch_sequence,
    requires_arm=True,
)

HOLD_COUNTDOWN = Tool(
    name="hold_countdown",
    description=(
        "Halt an in-progress countdown (stops it where it is). Lights LED 9 (Hold), plays "
        "SFX-CAUTION, writes HOLD to LCD line 1. Not arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_hold_countdown,
    requires_arm=False,
)

RANGE_SAFETY_DESTRUCT = Tool(
    name="range_safety_destruct",
    description=(
        "Issue range-safety destruct command (simulated). Requires S4 "
        "Range Safety toggle on; otherwise refuses. Lights LEDs 31-50, "
        "plays SFX-ALARM, renders BREACH on OLED B. Arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_range_safety_destruct,
    requires_arm=True,
)


SPACE_COMMAND_TOOLS: list[Tool] = [
    INITIATE_LAUNCH,
    HOLD_COUNTDOWN,
    RANGE_SAFETY_DESTRUCT,
]


# ── Scenario construction (from emitted YAML) ────────────────────────────


def build_scenario(emitted_path: Optional[Path] = None) -> Scenario:
    """Construct the Space Command Launch ``Scenario`` from the emitted YAML."""
    return build_from_emitted(
        "space_command_launch",
        tools=SPACE_COMMAND_TOOLS,
        default_title="Space Command Launch",
        default_voice="ryan",
        emitted_path=emitted_path,
    )


# Module-level singleton for the common case (importers who don't care
# about reloading the YAML on each construction).
SPACE_COMMAND_LAUNCH: Scenario = build_scenario()
