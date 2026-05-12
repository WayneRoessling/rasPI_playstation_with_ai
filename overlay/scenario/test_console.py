"""Minimal 'Test Console' scenario — for pipeline verification only.

This is NOT one of the six real scenarios (Space Command, Spaceship
Cockpit, Pirate Ship, Mars Control normal/disaster, Army Battle Command);
those land in Drop 3 with full narratives in `overlay/narratives/`.

`test_console` exists so the HAL client and Ollama tool-use loop can be
exercised end-to-end against the simulator without a complete narrative
authoring round-trip.
"""
from .runtime import Scenario
from .tools import GENERIC_TOOLS, Tool, _exec_play_sfx


# A demonstration of an arm-gated tool: same as play_sfx but only
# permitted when the MT-301 key is in ARM. Useful for verifying the
# arm-gate path in the runtime.
def _exec_play_alarm_armed(hal, args):
    # Force slot 4 (ALARM); ignore caller args
    return _exec_play_sfx(hal, {"slot": 4})


PLAY_ALARM_ARMED = Tool(
    name="trigger_emergency_alarm",
    description=(
        "Trigger the panel's red emergency alarm klaxon. Only available "
        "when the safety key is in ARM."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_exec_play_alarm_armed,
    requires_arm=True,
)


TEST_CONSOLE = Scenario(
    name="Test Console",
    voice="lessac",
    persona_prompt=(
        "You are the voice of a development test console. You speak "
        "briefly and clearly, like a friendly mission-control operator. "
        "You acknowledge actions you take and report state when asked. "
        "Default to actions over chatter."
    ),
    tools=list(GENERIC_TOOLS) + [PLAY_ALARM_ARMED],
    switch_labels=[
        "Main Power", "Aux Power",  "Comms",    "Radar",   "Beacon",
        "Backup",     "Override",   "Test",     "Spare 1", "Spare 2",
    ],
)
