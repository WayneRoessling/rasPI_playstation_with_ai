"""LLM tools — function descriptors + execution adapters.

Each Tool has:
  - `descriptor`: Ollama / OpenAI-format function spec sent to the LLM
  - `execute(hal, args)`: synchronous Python that runs the HAL command
                          and returns a short string for the LLM
  - `requires_arm`: if True, the runtime refuses the call unless the
                    MT-301 key switch is in ARM (see HAL_PROTOCOL §7).

Add scenario-specific tools by constructing your own `Tool` instances
in the scenario's tool list. The generic set below covers the common
cases (lights, sounds, displays).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    execute: Callable[..., str]
    requires_arm: bool = False

    @property
    def descriptor(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ── Generic execution functions ──────────────────────────────────────────


def _exec_play_sfx(hal, args: dict) -> str:
    slot = int(args.get("slot", 0))
    if not 1 <= slot <= 10:
        return f"error: slot {slot} out of range (1-10)"
    hal.play_sfx(slot)
    return f"ok: played sfx slot {slot}"


def _exec_set_led(hal, args: dict) -> str:
    led_id = int(args["id"])
    on = bool(args.get("on", True))
    if not 1 <= led_id <= 50:
        return f"error: led id {led_id} out of range (1-50)"
    hal.set_led(led_id, on)
    return f"ok: LED {led_id} -> {'on' if on else 'off'}"


def _exec_set_leds_range(hal, args: dict) -> str:
    start = int(args["start"])
    end = int(args["end"])
    on = bool(args.get("on", True))
    if not 1 <= start <= 50 or not 1 <= end <= 50 or end < start:
        return f"error: invalid range {start}..{end}"
    for i in range(start, end + 1):
        hal.set_led(i, on)
    return f"ok: LEDs {start}-{end} -> {'on' if on else 'off'}"


def _exec_clear_leds(hal, args: dict) -> str:
    hal.clear_leds()
    return "ok: all LEDs off"


def _exec_write_lcd(hal, args: dict) -> str:
    line = int(args.get("line", 1))
    text = str(args.get("text", ""))[:16]
    if line not in (1, 2):
        return f"error: line {line} (must be 1 or 2)"
    hal.write_lcd(line, text)
    return f"ok: LCD line {line} = {text!r}"


def _exec_clear_lcd(hal, args: dict) -> str:
    hal.clear_lcd()
    return "ok: LCD cleared"


def _exec_oled_status(hal, args: dict) -> str:
    display = args.get("display", "MASTER")
    hal.render_oled(display, "status", {
        "scenario": str(args.get("scenario", ""))[:21],
        "arm": str(args.get("arm", "SAFE")),
        "health": str(args.get("health", "OK"))[:21],
    })
    return f"ok: {display} showing status"


def _exec_oled_alert(hal, args: dict) -> str:
    display = args.get("display", "B")
    hal.render_oled(display, "alert", {
        "title": str(args.get("title", ""))[:12],
        "subtitle": str(args.get("subtitle", ""))[:21],
    })
    return f"ok: {display} showing alert {args.get('title')!r}"


def _exec_oled_text(hal, args: dict) -> str:
    display = args.get("display", "B")
    lines = args.get("lines", [])
    if not isinstance(lines, list):
        return "error: lines must be an array of strings"
    hal.render_oled(display, "text", {"lines": [str(s)[:21] for s in lines[:6]]})
    return f"ok: {display} showing {len(lines)} text lines"


# ── Built-in tool catalog ────────────────────────────────────────────────

PLAY_SFX = Tool(
    name="play_sfx",
    description=(
        "Play a short sound effect from the panel's 10-slot SFX bank. "
        "1=ack 2=deny 3=caution 4=alarm 5=arm 6=disarm "
        "7=comms 8=click 9=tick 10=status."
    ),
    parameters={
        "type": "object",
        "properties": {
            "slot": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        "required": ["slot"],
    },
    execute=_exec_play_sfx,
)

SET_LED = Tool(
    name="set_led",
    description="Turn a single LED on the panel on or off. LED ids are 1-50.",
    parameters={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "minimum": 1, "maximum": 50},
            "on": {"type": "boolean"},
        },
        "required": ["id", "on"],
    },
    execute=_exec_set_led,
)

SET_LEDS_RANGE = Tool(
    name="set_leds_range",
    description="Turn a contiguous range of LEDs on or off (inclusive).",
    parameters={
        "type": "object",
        "properties": {
            "start": {"type": "integer", "minimum": 1, "maximum": 50},
            "end":   {"type": "integer", "minimum": 1, "maximum": 50},
            "on":    {"type": "boolean"},
        },
        "required": ["start", "end", "on"],
    },
    execute=_exec_set_leds_range,
)

CLEAR_LEDS = Tool(
    name="clear_leds",
    description="Turn off every LED on the panel.",
    parameters={"type": "object", "properties": {}},
    execute=_exec_clear_leds,
)

WRITE_LCD = Tool(
    name="write_lcd",
    description="Write one line (1 or 2) of the 1602 character LCD. Each line is 16 characters; longer text is truncated.",
    parameters={
        "type": "object",
        "properties": {
            "line": {"type": "integer", "minimum": 1, "maximum": 2},
            "text": {"type": "string"},
        },
        "required": ["line", "text"],
    },
    execute=_exec_write_lcd,
)

CLEAR_LCD = Tool(
    name="clear_lcd",
    description="Clear the 1602 character LCD.",
    parameters={"type": "object", "properties": {}},
    execute=_exec_clear_lcd,
)

OLED_STATUS = Tool(
    name="render_oled_status",
    description="Render a status block on one of the OLED displays. MASTER is the always-visible status display next to the safety key.",
    parameters={
        "type": "object",
        "properties": {
            "display":  {"type": "string", "enum": ["B", "MASTER"]},
            "scenario": {"type": "string"},
            "arm":      {"type": "string", "enum": ["ARMED", "SAFE"]},
            "health":   {"type": "string"},
        },
        "required": ["display"],
    },
    execute=_exec_oled_status,
)

OLED_ALERT = Tool(
    name="render_oled_alert",
    description="Render a large title + subtitle alert on one of the OLED displays.",
    parameters={
        "type": "object",
        "properties": {
            "display":  {"type": "string", "enum": ["B", "MASTER"]},
            "title":    {"type": "string"},
            "subtitle": {"type": "string"},
        },
        "required": ["display", "title"],
    },
    execute=_exec_oled_alert,
)

OLED_TEXT = Tool(
    name="render_oled_text",
    description="Render up to 6 lines of text on one of the OLED displays.",
    parameters={
        "type": "object",
        "properties": {
            "display": {"type": "string", "enum": ["B", "MASTER"]},
            "lines":   {"type": "array", "items": {"type": "string"}},
        },
        "required": ["display", "lines"],
    },
    execute=_exec_oled_text,
)


GENERIC_TOOLS: list[Tool] = [
    PLAY_SFX,
    SET_LED, SET_LEDS_RANGE, CLEAR_LEDS,
    WRITE_LCD, CLEAR_LCD,
    OLED_STATUS, OLED_ALERT, OLED_TEXT,
]
