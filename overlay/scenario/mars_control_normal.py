"""Mars Control Center — Normal Operations.

Built from the emitted YAML at
``overlay/narratives/scenarios/mars_control_normal/_emitted/scenario.yaml``.

This is the calm sibling of ``mars_control_disaster`` — same physical
panel and switch labels, different persona + different tool set.

Three scenario-specific tools, none arm-gated:

* ``daily_systems_check`` — SFX-COMMS + 10 ticks + LEDs 11-20 ramp +
  SFX-ACK at completion.
* ``query_resource`` — takes a resource name and writes a stock
  summary to LCD + OLED B.
* ``schedule_eva`` — takes optional crew/bearing parameters and
  writes a 3-line EVA plan to OLED B.
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
    / "mars_control_normal"
    / "_emitted"
    / "scenario.yaml"
)


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


# Static resource dictionary for query_resource. Future iteration could
# read from a slow-drift colony simulation.
RESOURCE_TABLE: dict[str, tuple[str, str]] = {
    "water":  ("WATER 92%",   "RECYC NOMINAL"),
    "oxygen": ("OXYGEN 96%",  "O2 LOOP GREEN"),
    "power":  ("POWER 78%",   "ARRAY NOMINAL"),
    "food":   ("FOOD 41 DAYS", "GROWTH ON SCHED"),
    "crew":   ("CREW 87/87",  "ALL ACCT FOR"),
}


def _exec_daily_systems_check(hal, args: dict) -> str:
    """Run the routine 10-step systems check. Not arm-gated."""
    del args

    hal.play_sfx(7)                       # SFX-COMMS — check begins
    hal.write_lcd(1, "DAILY CHECK")
    hal.write_lcd(2, "STEP 0/10")

    for step in range(1, 11):
        hal.set_led(10 + step, on=True)
        hal.write_lcd(2, f"STEP {step}/10")
        hal.play_sfx(9)                   # SFX-TICK
        time.sleep(1.0)

    hal.write_lcd(1, "CHECK COMPLETE")
    hal.write_lcd(2, "ALL NOMINAL")
    hal.play_sfx(1)                       # SFX-ACK at completion
    return "ok: daily check complete; all 10 steps nominal"


def _exec_query_resource(hal, args: dict) -> str:
    """Read a single named resource to LCD + OLED B."""
    name = str(args.get("name", "")).strip().lower()
    if name not in RESOURCE_TABLE:
        return (
            f"error: unknown resource {name!r} — "
            f"expected one of {sorted(RESOURCE_TABLE)}"
        )

    line1, line2 = RESOURCE_TABLE[name]
    hal.play_sfx(1)                       # SFX-ACK
    hal.write_lcd(1, line1)
    hal.write_lcd(2, line2)
    hal.render_oled("B", "text", {
        "lines": [
            f"Resource: {name}",
            line1,
            line2,
            "Trend: stable",
        ],
    })
    return f"ok: {name} reported ({line1.lower()})"


def _exec_schedule_eva(hal, args: dict) -> str:
    """Schedule an EVA — writes a 3-line plan to OLED B."""
    crew = str(args.get("crew", "Choi, Park"))[:21]
    bearing = str(args.get("bearing", "042"))[:21]

    hal.play_sfx(10)                      # SFX-STATUS
    hal.write_lcd(1, "EVA SCHEDULED")
    hal.write_lcd(2, f"BRG {bearing[:11]}")
    hal.render_oled("B", "text", {
        "lines": [
            "EVA SCHEDULED",
            f"Crew: {crew}",
            f"Bearing: {bearing}",
            "Suit prebreathe: 30m",
        ],
    })
    return f"ok: EVA scheduled (crew={crew}, bearing={bearing})"


DAILY_SYSTEMS_CHECK = Tool(
    name="daily_systems_check",
    description=(
        "Run the routine 10-step Mars Base systems check. Plays "
        "SFX-COMMS once, then SFX-TICK ten times at 1 s intervals "
        "while lighting LEDs 11-20 sequentially and writing STEP n/10 "
        "to LCD line 2, then SFX-ACK with CHECK COMPLETE on the LCD. "
        "Not arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_daily_systems_check,
    requires_arm=False,
)

QUERY_RESOURCE = Tool(
    name="query_resource",
    description=(
        "Read out one named resource (water|oxygen|power|food|crew) "
        "to the LCD and OLED B. Plays SFX-ACK. Not arm-gated."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "enum": ["water", "oxygen", "power", "food", "crew"],
            },
        },
        "required": ["name"],
    },
    execute=_exec_query_resource,
    requires_arm=False,
)

SCHEDULE_EVA = Tool(
    name="schedule_eva",
    description=(
        "Schedule an EVA. Writes a 3-line plan (EVA SCHEDULED + crew + "
        "bearing + prebreathe) to OLED B, plays SFX-STATUS. Not "
        "arm-gated."
    ),
    parameters={
        "type": "object",
        "properties": {
            "crew":    {"type": "string"},
            "bearing": {"type": "string"},
        },
    },
    execute=_exec_schedule_eva,
    requires_arm=False,
)


MARS_NORMAL_TOOLS: list[Tool] = [
    DAILY_SYSTEMS_CHECK,
    QUERY_RESOURCE,
    SCHEDULE_EVA,
]


def _load_emitted(path: Optional[Path] = None) -> dict:
    src = path or EMITTED_YAML
    if not src.exists():
        raise FileNotFoundError(
            f"emitted scenario YAML not found at {src}.\n"
            "Run: python overlay/tools/emit_scenarios.py mars_control_normal"
        )
    with src.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{src}: emitted YAML is not a mapping")
    return data


def build_scenario(emitted_path: Optional[Path] = None) -> Scenario:
    """Construct the Mars Control Normal ``Scenario`` from the emitted YAML."""
    data = _load_emitted(emitted_path)
    labels = data.get("switch_labels") or []
    if len(labels) != 10:
        raise ValueError("emitted scenario has fewer than 10 switch_labels")

    return Scenario(
        name=data.get("title", "Mars Control Center — Normal Operations"),
        voice=data.get("voice", "lessac"),
        persona_prompt=data.get("persona_prompt", ""),
        tools=list(GENERIC_TOOLS) + MARS_NORMAL_TOOLS,
        switch_labels=[str(s) for s in labels],
        sfx_role_names=list(data.get("sfx_role_names") or [
            "ack", "deny", "caution", "alarm", "arm",
            "disarm", "comms", "click", "tick", "status",
        ]),
    )


MARS_CONTROL_NORMAL: Scenario = build_scenario()
