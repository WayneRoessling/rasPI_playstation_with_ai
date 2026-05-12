"""Pirate Space Ship — irreverent free-trader vessel.

Built from the emitted YAML at
``overlay/narratives/scenarios/pirate_ship/_emitted/scenario.yaml``.

Three scenario-specific tools, none arm-gated (pirates are reckless):

* ``fire_cannon`` — SFX-ALARM + LEDs 31-40 + FIRE! on LCD.
* ``raise_jolly_roger`` — SFX-STATUS + LED 3 + LEDs 21-25 pennant rise.
* ``dispense_grog`` — SFX-ACK + GROG RATION on LCD.
"""

from __future__ import annotations

import itertools
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
    / "pirate_ship"
    / "_emitted"
    / "scenario.yaml"
)


SWITCH_LABELS: dict[int, str] = {
    1: "Plunder Hold",
    2: "Grog Stock",
    3: "Black Flag",
    4: "Plank Lock",
    5: "Bilge Pump",
    6: "Crow's Nest",
    7: "Powder Magazine",
    8: "Sails",
    9: "Anchor",
    10: "Parley Lamp",
}


# Rotating gun-crew callouts so successive fire_cannon calls feel
# different. itertools.cycle is module-level so the rotation persists
# across calls within one process.
_GUN_CREW_CYCLE = itertools.cycle(
    ("PORT GUN CREW", "STARBOARD GUNS", "BOW CHASER")
)
_TOAST_CYCLE = itertools.cycle(
    ("TO THE PRIZE", "TO ABSENT FRIENDS", "TO TOMORROW")
)


def _exec_fire_cannon(hal, args: dict) -> str:
    """Fire the port broadside. Not arm-gated."""
    del args
    crew = next(_GUN_CREW_CYCLE)
    for led in range(31, 41):
        hal.set_led(led, on=True)
    hal.play_sfx(4)                       # SFX-ALARM
    hal.write_lcd(1, "FIRE!")
    hal.write_lcd(2, crew[:16])
    return f"ok: broadside away ({crew.lower()})"


def _exec_raise_jolly_roger(hal, args: dict) -> str:
    """Hoist the black flag — sequenced pennant rise."""
    del args
    hal.set_led(3, on=True)               # S3 Black Flag mirror
    # Pennant rise: light LEDs 21..25 step-by-step
    for led in range(21, 26):
        hal.set_led(led, on=True)
        time.sleep(0.2)
    hal.play_sfx(10)                      # SFX-STATUS
    hal.write_lcd(1, "COLOURS UP")
    return "ok: jolly roger hoisted"


def _exec_dispense_grog(hal, args: dict) -> str:
    """Pour the crew a round."""
    del args
    toast = next(_TOAST_CYCLE)
    hal.play_sfx(1)                       # SFX-ACK
    hal.write_lcd(1, "GROG RATION")
    hal.write_lcd(2, toast[:16])
    return f"ok: ration dispensed ({toast.lower()})"


FIRE_CANNON = Tool(
    name="fire_cannon",
    description=(
        "Fire the port broadside. Pirates do not arm-gate cannon fire. "
        "Plays SFX-ALARM, lights LEDs 31-40 (gunnery band), writes "
        "FIRE! on LCD line 1 and the gun-crew callout on line 2. "
        "Not arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_fire_cannon,
    requires_arm=False,
)

RAISE_JOLLY_ROGER = Tool(
    name="raise_jolly_roger",
    description=(
        "Hoist the black flag. Plays SFX-STATUS, lights LED 3 (Black "
        "Flag mirror) and LEDs 21-25 as a pennant-rise indicator, "
        "writes COLOURS UP on LCD line 1. Not arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_raise_jolly_roger,
    requires_arm=False,
)

DISPENSE_GROG = Tool(
    name="dispense_grog",
    description=(
        "Pour the crew a round. Plays SFX-ACK, writes GROG RATION on "
        "LCD line 1 and a rotating toast on line 2. Not arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_dispense_grog,
    requires_arm=False,
)


PIRATE_SHIP_TOOLS: list[Tool] = [
    FIRE_CANNON,
    RAISE_JOLLY_ROGER,
    DISPENSE_GROG,
]


def _load_emitted(path: Optional[Path] = None) -> dict:
    src = path or EMITTED_YAML
    if not src.exists():
        raise FileNotFoundError(
            f"emitted scenario YAML not found at {src}.\n"
            "Run: python overlay/tools/emit_scenarios.py pirate_ship"
        )
    with src.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{src}: emitted YAML is not a mapping")
    return data


def build_scenario(emitted_path: Optional[Path] = None) -> Scenario:
    """Construct the Pirate Ship ``Scenario`` from the emitted YAML."""
    data = _load_emitted(emitted_path)
    labels = data.get("switch_labels") or []
    if len(labels) != 10:
        raise ValueError("emitted scenario has fewer than 10 switch_labels")

    return Scenario(
        name=data.get("title", "Pirate Space Ship"),
        voice=data.get("voice", "alan"),
        persona_prompt=data.get("persona_prompt", ""),
        tools=list(GENERIC_TOOLS) + PIRATE_SHIP_TOOLS,
        switch_labels=[str(s) for s in labels],
        sfx_role_names=list(data.get("sfx_role_names") or [
            "ack", "deny", "caution", "alarm", "arm",
            "disarm", "comms", "click", "tick", "status",
        ]),
    )


PIRATE_SHIP: Scenario = build_scenario()
