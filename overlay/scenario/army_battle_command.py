"""Army Battle Command Center — battalion TOC console.

Built from the emitted YAML at
``overlay/narratives/scenarios/army_battle_command/_emitted/scenario.yaml``.

The most arm-gated of the six scenarios.

Three scenario-specific tools:

* ``engage_target`` — arm-gated + S3 Weapons Free + S4 ROE Active.
  SFX-ALARM + LEDs 31-40 + LCD ENGAGE / target.
* ``request_isr`` — not arm-gated. SFX-COMMS + LCD + OLED B overpass
  details.
* ``call_counter_battery`` — arm-gated + S9 required. SFX-ALARM +
  LEDs 41-50 + LCD COUNTER-BTRY / grid + OLED B alert.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .runtime import Scenario
from .loader import build_from_emitted
from .tools import Tool




# Required switches for `engage_target` — S3 Weapons Free, S4 ROE Active
ENGAGE_REQUIRED_SWITCHES: tuple[int, ...] = (3, 4)

SWITCH_LABELS: dict[int, str] = {
    1: "C2 Link",
    2: "ISR Feed",
    3: "Weapons Free",
    4: "ROE Active",
    5: "EMCON",
    6: "Comms Sec",
    7: "Drone Net",
    8: "AAA Battery",
    9: "Counter-Battery",
    10: "Stand-To",
}


def _exec_engage_target(hal, args: dict) -> str:
    """Engage a tactical target. Arm-gated + requires S3 + S4 on."""
    target_id = str(args.get("target_id", "")).strip().upper()[:14]
    if not target_id:
        return "error: target_id is required"

    state = hal.state()
    switches = state.get("switches") or [0] * 10
    missing = [
        SWITCH_LABELS[i] for i in ENGAGE_REQUIRED_SWITCHES
        if not switches[i - 1]
    ]
    if missing:
        return f"refused: engagement checklist incomplete: {', '.join(missing)}"

    # Fires band
    for led in range(31, 41):
        hal.set_led(led, on=True)
    hal.play_sfx(4)                       # SFX-ALARM
    hal.write_lcd(1, "ENGAGE")
    hal.write_lcd(2, target_id[:16])
    return f"ok: engaging {target_id}"


def _exec_request_isr(hal, args: dict) -> str:
    """Request ISR overpass. Not arm-gated."""
    bearing = str(args.get("bearing", "045")).strip()[:16]

    hal.play_sfx(7)                       # SFX-COMMS
    hal.write_lcd(1, "ISR REQ")
    hal.write_lcd(2, f"BRG {bearing[:11]}")
    hal.render_oled("B", "text", {
        "lines": [
            "ISR REQUEST",
            f"Bearing: {bearing}",
            "Asset: organic drone",
            "ETA: 4 min",
            "Frame: full motion",
        ],
    })
    return f"ok: ISR requested on bearing {bearing}"


def _exec_call_counter_battery(hal, args: dict) -> str:
    """Counter-battery fire. Arm-gated + requires S9 on."""
    grid = str(args.get("grid", "")).strip().upper()[:14]
    if not grid:
        return "error: grid is required"

    state = hal.state()
    switches = state.get("switches") or [0] * 10
    if not switches[8]:                   # S9 index = 8
        return "refused: counter-battery authorization is open"

    # Counter-battery band
    for led in range(41, 51):
        hal.set_led(led, on=True)
    hal.play_sfx(4)                       # SFX-ALARM
    hal.write_lcd(1, "COUNTER-BTRY")
    hal.write_lcd(2, grid[:16])
    hal.render_oled("B", "alert", {
        "title": "CTR-BTRY",
        "subtitle": f"grid {grid}",
    })
    return f"ok: counter-battery on grid {grid}"


ENGAGE_TARGET = Tool(
    name="engage_target",
    description=(
        "Engage a tactical target. Validates S3 Weapons Free and S4 "
        "ROE Active are on; refuses with the missing list otherwise. "
        "Takes target_id. Plays SFX-ALARM, lights LEDs 31-40 (fires "
        "band), writes ENGAGE + target on the LCD. Arm-gated."
    ),
    parameters={
        "type": "object",
        "properties": {
            "target_id": {
                "type": "string",
                "description": "target identifier (e.g. TGT-04)",
            },
        },
        "required": ["target_id"],
    },
    execute=_exec_engage_target,
    requires_arm=True,
)

REQUEST_ISR = Tool(
    name="request_isr",
    description=(
        "Request ISR overpass. Plays SFX-COMMS, writes ISR REQ + "
        "bearing on the LCD, renders overpass details on OLED B. "
        "Not arm-gated."
    ),
    parameters={
        "type": "object",
        "properties": {
            "bearing": {
                "type": "string",
                "description": "compass bearing for the overpass",
            },
        },
    },
    execute=_exec_request_isr,
    requires_arm=False,
)

CALL_COUNTER_BATTERY = Tool(
    name="call_counter_battery",
    description=(
        "Call counter-battery fire. Requires S9 Counter-Battery toggle "
        "on; otherwise refuses. Takes grid. Plays SFX-ALARM, lights "
        "LEDs 41-50, writes COUNTER-BTRY + grid on the LCD, renders "
        "alert on OLED B. Arm-gated."
    ),
    parameters={
        "type": "object",
        "properties": {
            "grid": {
                "type": "string",
                "description": "target grid reference",
            },
        },
        "required": ["grid"],
    },
    execute=_exec_call_counter_battery,
    requires_arm=True,
)


ARMY_BATTLE_TOOLS: list[Tool] = [
    ENGAGE_TARGET,
    REQUEST_ISR,
    CALL_COUNTER_BATTERY,
]


def build_scenario(emitted_path: Optional[Path] = None) -> Scenario:
    """Construct the Army Battle Command ``Scenario`` from the emitted YAML."""
    return build_from_emitted(
        "army_battle_command",
        tools=ARMY_BATTLE_TOOLS,
        default_title="Army Battle Command Center",
        default_voice="ryan",
        emitted_path=emitted_path,
    )


# Module-level singleton for the common case (importers who don't care
# about reloading the YAML on each construction).
ARMY_BATTLE_COMMAND: Scenario = build_scenario()
