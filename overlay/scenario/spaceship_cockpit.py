"""Spaceship Cockpit — civilian deep-space exploration vessel.

Built from the emitted YAML at
``overlay/narratives/scenarios/spaceship_cockpit/_emitted/scenario.yaml``;
re-running ``overlay/tools/emit_scenarios.py spaceship_cockpit``
regenerates that YAML.

Three scenario-specific tools on top of the generic set:

* ``engage_warp_drive`` — arm-gated; validates Warp Coil (S6) and
  Impulse (S7); plays SFX-COMMS, a 5-step warp ramp (LEDs 11-15 +
  SFX-TICK), and SFX-STATUS at lock.
* ``scan_sector`` — not arm-gated; plays SFX-COMMS, writes scan
  summary to the LCD, renders a 6-line contact list on OLED B.
* ``vent_airlock`` — arm-gated AND requires S10 Airlock on; plays
  SFX-ALARM and renders ALERT: VENT on OLED B.
"""

from __future__ import annotations

import random
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
    / "spaceship_cockpit"
    / "_emitted"
    / "scenario.yaml"
)


# Required switches for `engage_warp_drive` — S6 Warp Coil and S7 Impulse.
WARP_REQUIRED_SWITCHES: tuple[int, ...] = (6, 7)

SWITCH_LABELS: dict[int, str] = {
    1: "Inertial Dampeners",
    2: "Life Support",
    3: "Nav Computer",
    4: "Tractor Beam",
    5: "Shields",
    6: "Warp Coil",
    7: "Impulse",
    8: "Sensors",
    9: "Cargo Bay",
    10: "Airlock",
}


# Small procedural bank of contact returns for `scan_sector` — chosen
# randomly per call so the panel feels alive turn-to-turn.
SCAN_CONTACT_BANK: tuple[tuple[str, ...], ...] = (
    ("Asteroid cluster 042 mark 3", "Comet C/2278 inbound",
     "Long-range static ambient", "No vessels in range", "Hull integrity 100%"),
    ("Dust field bearing 217", "Pulsar signature port quarter",
     "Cargo container drift 011", "Sensor noise floor stable", "All clear"),
    ("Gas giant moonlet 088", "Solar wind variance 4%",
     "Faint comms echo 350 MHz", "No threats", "Shields nominal"),
)


def _exec_engage_warp_drive(hal, args: dict) -> str:
    """Ramp warp drive — requires S6 and S7 on; 5-step LED ramp + ticks."""
    del args

    state = hal.state()
    switches = state.get("switches") or [0] * 10
    missing = [
        SWITCH_LABELS[i] for i in WARP_REQUIRED_SWITCHES
        if not switches[i - 1]
    ]
    if missing:
        return f"refused: warp checklist incomplete: {', '.join(missing)}"

    hal.play_sfx(7)                       # SFX-COMMS — drive online

    hal.write_lcd(1, "ENGAGING WARP")
    hal.write_lcd(2, "WARP 0.0")

    # 5-second ramp: light LEDs 11..15 step by step, tick once per step,
    # update LCD line 2 with the current warp factor.
    for step in range(1, 6):
        hal.set_led(10 + step, on=True)
        hal.write_lcd(2, f"WARP {step}.0")
        hal.play_sfx(9)                   # SFX-TICK
        time.sleep(1.0)

    hal.write_lcd(1, "WARP ACTIVE")
    hal.play_sfx(10)                      # SFX-STATUS at lock
    return "ok: warp engaged at factor 5"


def _exec_scan_sector(hal, args: dict) -> str:
    """Sweep sensors — SFX-COMMS, scan summary on LCD + contact list on OLED B."""
    del args
    contacts = random.choice(SCAN_CONTACT_BANK)
    summary = contacts[0][:16]

    hal.play_sfx(7)                       # SFX-COMMS
    hal.write_lcd(1, "SECTOR SCAN")
    hal.write_lcd(2, summary)
    hal.render_oled("B", "text", {"lines": list(contacts)})
    return f"ok: scan complete; {len(contacts)} contacts reported"


def _exec_vent_airlock(hal, args: dict) -> str:
    """Vent the starboard airlock. Arm-gated AND requires S10 Airlock on."""
    del args
    state = hal.state()
    switches = state.get("switches") or [0] * 10
    if not switches[9]:                   # S10 index = 9
        return "refused: airlock interlock is closed"
    for led in range(31, 41):
        hal.set_led(led, on=True)
    hal.play_sfx(4)                       # SFX-ALARM
    hal.render_oled("B", "alert", {"title": "ALERT: VENT", "subtitle": "starboard airlock"})
    return "ok: airlock vented"


ENGAGE_WARP_DRIVE = Tool(
    name="engage_warp_drive",
    description=(
        "Engage the warp drive. Validates S6 Warp Coil and S7 Impulse "
        "are on; refuses with the missing list otherwise. Plays "
        "SFX-COMMS, then a 5-step warp ramp (LEDs 11-15 + SFX-TICK + "
        "LCD WARP n.n), then SFX-STATUS at lock with LCD = WARP "
        "ACTIVE. Arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_engage_warp_drive,
    requires_arm=True,
)

SCAN_SECTOR = Tool(
    name="scan_sector",
    description=(
        "Sweep the long-range sensors. Plays SFX-COMMS, writes SECTOR "
        "SCAN + summary on the LCD, renders a 6-line contact list on "
        "OLED B. Not arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_scan_sector,
    requires_arm=False,
)

VENT_AIRLOCK = Tool(
    name="vent_airlock",
    description=(
        "Vent the starboard airlock. Requires S10 Airlock toggle on; "
        "otherwise refuses. Plays SFX-ALARM, lights LEDs 31-40, "
        "renders ALERT: VENT on OLED B. Arm-gated."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_vent_airlock,
    requires_arm=True,
)


SPACESHIP_COCKPIT_TOOLS: list[Tool] = [
    ENGAGE_WARP_DRIVE,
    SCAN_SECTOR,
    VENT_AIRLOCK,
]


def _load_emitted(path: Optional[Path] = None) -> dict:
    src = path or EMITTED_YAML
    if not src.exists():
        raise FileNotFoundError(
            f"emitted scenario YAML not found at {src}.\n"
            "Run: python overlay/tools/emit_scenarios.py spaceship_cockpit"
        )
    with src.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{src}: emitted YAML is not a mapping")
    return data


def build_scenario(emitted_path: Optional[Path] = None) -> Scenario:
    """Construct the Spaceship Cockpit ``Scenario`` from the emitted YAML."""
    data = _load_emitted(emitted_path)
    labels = data.get("switch_labels") or []
    if len(labels) != 10:
        raise ValueError("emitted scenario has fewer than 10 switch_labels")

    return Scenario(
        name=data.get("title", "Spaceship Cockpit"),
        voice=data.get("voice", "amy"),
        persona_prompt=data.get("persona_prompt", ""),
        tools=list(GENERIC_TOOLS) + SPACESHIP_COCKPIT_TOOLS,
        switch_labels=[str(s) for s in labels],
        sfx_role_names=list(data.get("sfx_role_names") or [
            "ack", "deny", "caution", "alarm", "arm",
            "disarm", "comms", "click", "tick", "status",
        ]),
    )


SPACESHIP_COCKPIT: Scenario = build_scenario()
