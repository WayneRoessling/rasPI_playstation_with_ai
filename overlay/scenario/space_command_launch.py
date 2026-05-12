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
  countdown LEDs.
* ``hold_countdown`` — not arm-gated; declares a hold.
* ``range_safety_destruct`` — arm-gated AND requires S4 Range Safety
  toggle on; simulated destruct cue.

Authored scenarios are not unit-tested at the Python level — they are
validated end-to-end by ``python -m overlay.scenario.demo --scenario
space_command_launch …`` against the simulator.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    sys.stderr.write("pyyaml required: pip install pyyaml\n")
    raise

from .runtime import Scenario
from .tools import GENERIC_TOOLS, Tool


OVERLAY_ROOT = Path(__file__).resolve().parent.parent
EMITTED_YAML = (
    OVERLAY_ROOT
    / "narratives"
    / "scenarios"
    / "space_command_launch"
    / "_emitted"
    / "scenario.yaml"
)


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

    # Light LEDs 11..20 and write T-N to LCD, paced by 1 s ticks. We pulse
    # one SFX-TICK per second through sfx_seq so the audio stays in time
    # with the LED march even if the Python loop drifts a few ms.
    for n in range(10, 0, -1):
        idx = 11 + (10 - n)             # 11..20
        hal.set_led(idx, on=True)
        hal.write_lcd(2, f"T-{n:02d}")
        hal.play_sfx(9)                 # SFX-TICK
        time.sleep(1.0)

    # T-0
    hal.write_lcd(1, "LIFTOFF")
    hal.write_lcd(2, "T-00")
    hal.play_sfx(10)                    # SFX-STATUS
    return "ok: launch sequence complete; liftoff"


def _exec_hold_countdown(hal, args: dict) -> str:
    """Declare a hold — yellow caution, hold LED, HOLD on LCD."""
    del args
    hal.set_led(9, on=True)             # Hold (S9 mirror)
    hal.play_sfx(3)                     # SFX-CAUTION
    hal.write_lcd(1, "HOLD")
    return "ok: hold declared"


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
        "list of missing switches otherwise. Plays comms chirp, then a "
        "10-second countdown (LEDs 11-20, SFX-TICK, LCD T-N), then "
        "SFX-STATUS at T-0 and LIFTOFF on the LCD. Arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_initiate_launch_sequence,
    requires_arm=True,
)

HOLD_COUNTDOWN = Tool(
    name="hold_countdown",
    description=(
        "Halt an in-progress countdown. Lights LED 9 (Hold), plays "
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


def _load_emitted(path: Optional[Path] = None) -> dict:
    src = path or EMITTED_YAML
    if not src.exists():
        raise FileNotFoundError(
            f"emitted scenario YAML not found at {src}.\n"
            "Run: python overlay/tools/emit_scenarios.py space_command_launch"
        )
    with src.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{src}: emitted YAML is not a mapping")
    return data


def build_scenario(emitted_path: Optional[Path] = None) -> Scenario:
    """Construct the Space Command Launch ``Scenario`` from the emitted YAML."""
    data = _load_emitted(emitted_path)
    labels = data.get("switch_labels") or []
    if len(labels) != 10:
        raise ValueError("emitted scenario has fewer than 10 switch_labels")

    return Scenario(
        name=data.get("title", "Space Command Launch"),
        voice=data.get("voice", "ryan"),
        persona_prompt=data.get("persona_prompt", ""),
        tools=list(GENERIC_TOOLS) + SPACE_COMMAND_TOOLS,
        switch_labels=[str(s) for s in labels],
        sfx_role_names=list(data.get("sfx_role_names") or [
            "ack", "deny", "caution", "alarm", "arm",
            "disarm", "comms", "click", "tick", "status",
        ]),
    )


# Module-level singleton for the common case (importers who don't care
# about reloading the YAML on each construction).
SPACE_COMMAND_LAUNCH: Scenario = build_scenario()
