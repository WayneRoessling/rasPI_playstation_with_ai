"""Mars Control Center — Disaster Response.

Built from the emitted YAML at
``overlay/narratives/scenarios/mars_control_disaster/_emitted/scenario.yaml``.

Twin scenario of ``mars_control_normal`` — same 10 switch labels, same
physical panel, sharpened persona, destructive tool set.

Three scenario-specific tools:

* ``evacuate_sector`` — arm-gated. SFX-ALARM + LEDs 31-50 + EVAC ORDER
  on OLED B.
* ``seal_habitat`` — not arm-gated (defensive). SFX-CAUTION + named
  habitat LED + LEDs 21-25 seal-progress.
* ``broadcast_mayday`` — not arm-gated. SFX-COMMS + SFX-ALARM +
  MAYDAY alert on OLED B.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .runtime import Scenario
from .loader import build_from_emitted
from .tools import Tool




SWITCH_LABELS: dict[int, str] = {
    1: "Habitat 1",
    2: "Habitat 2",
    3: "Greenhouse",
    4: "Solar Array",
    5: "Water Recycler",
    6: "Comms Array",
    7: "Rover Bay",
    8: "Reactor",
    9: "Cryo Lab",
    10: "Surface Lock",
}


# Map habitat names to switch indices for seal_habitat
HABITAT_MAP: dict[str, int | None] = {
    "hab1":       1,
    "hab2":       2,
    "greenhouse": 3,
    "cryo":       9,
    "all":        None,  # all habitats
}


def _exec_evacuate_sector(hal, args: dict) -> str:
    """Order evacuation. Arm-gated. Defaults to whole-base evac."""
    sector = str(args.get("sector", "all")).strip().lower()[:21]

    # Full alarm cluster
    for led in range(31, 51):
        hal.set_led(led, on=True)
    hal.play_sfx(4)                       # SFX-ALARM
    hal.write_lcd(1, "EVAC SECTOR")
    hal.write_lcd(2, sector[:16])
    hal.render_oled("B", "alert", {
        "title": "EVAC ORDER",
        "subtitle": f"sector {sector}",
    })
    return f"ok: evacuation ordered for {sector}"


def _exec_seal_habitat(hal, args: dict) -> str:
    """Seal the named habitat. Not arm-gated (defensive action)."""
    habitat = str(args.get("habitat", "")).strip().lower()
    if habitat not in HABITAT_MAP:
        return (
            f"error: unknown habitat {habitat!r} — "
            f"expected one of {sorted(HABITAT_MAP)}"
        )

    hal.play_sfx(3)                       # SFX-CAUTION

    # Light the named habitat's switch-mirror LED (or all if "all")
    sw_id = HABITAT_MAP[habitat]
    if sw_id is None:
        for i in (1, 2, 3, 9):            # all habitat-adjacent switches
            hal.set_led(i, on=True)
    else:
        hal.set_led(sw_id, on=True)

    # Seal-progress ramp on LEDs 21..25
    for led in range(21, 26):
        hal.set_led(led, on=True)
        time.sleep(0.15)

    hal.write_lcd(1, f"SEALED {habitat}"[:16])
    hal.write_lcd(2, "PRESSURE OK")
    return f"ok: {habitat} sealed"


def _exec_broadcast_mayday(hal, args: dict) -> str:
    """Broadcast mayday on the comms array. Not arm-gated."""
    del args
    hal.play_sfx(7)                       # SFX-COMMS — channel open
    time.sleep(0.4)
    hal.play_sfx(4)                       # SFX-ALARM — distress
    hal.write_lcd(1, "MAYDAY OUT")
    hal.write_lcd(2, "MARS BASE")
    hal.render_oled("B", "alert", {
        "title": "MAYDAY",
        "subtitle": "Mars Base distress",
    })
    return "ok: mayday broadcast initiated"


EVACUATE_SECTOR = Tool(
    name="evacuate_sector",
    description=(
        "Order evacuation of a named sector (default: all habitats). "
        "Plays SFX-ALARM, lights LEDs 31-50, renders EVAC ORDER alert "
        "on OLED B, writes EVAC SECTOR + sector name on the LCD. "
        "Arm-gated."
    ),
    parameters={
        "type": "object",
        "properties": {
            "sector": {
                "type": "string",
                "description": "sector name (hab1|hab2|all|greenhouse|cryo)",
            },
        },
    },
    execute=_exec_evacuate_sector,
    requires_arm=True,
)

SEAL_HABITAT = Tool(
    name="seal_habitat",
    description=(
        "Seal the named habitat against pressure breach. Plays "
        "SFX-CAUTION, lights the habitat's switch-mirror LED plus "
        "LEDs 21-25 as a seal-progress indicator, writes SEALED hab-N "
        "on the LCD. Not arm-gated (defensive action)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "habitat": {
                "type": "string",
                "enum": ["hab1", "hab2", "greenhouse", "cryo", "all"],
            },
        },
        "required": ["habitat"],
    },
    execute=_exec_seal_habitat,
    requires_arm=False,
)

BROADCAST_MAYDAY = Tool(
    name="broadcast_mayday",
    description=(
        "Broadcast mayday over the comms array. Plays SFX-COMMS once "
        "then SFX-ALARM, renders MAYDAY alert on OLED B, writes MAYDAY "
        "OUT on the LCD. Not arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_broadcast_mayday,
    requires_arm=False,
)


MARS_DISASTER_TOOLS: list[Tool] = [
    EVACUATE_SECTOR,
    SEAL_HABITAT,
    BROADCAST_MAYDAY,
]


def build_scenario(emitted_path: Optional[Path] = None) -> Scenario:
    """Construct the Mars Control Disaster ``Scenario`` from the emitted YAML."""
    return build_from_emitted(
        "mars_control_disaster",
        tools=MARS_DISASTER_TOOLS,
        default_title="Mars Control Center — Disaster Response",
        default_voice="lessac",
        emitted_path=emitted_path,
    )


# Module-level singleton for the common case (importers who don't care
# about reloading the YAML on each construction).
MARS_CONTROL_DISASTER: Scenario = build_scenario()
