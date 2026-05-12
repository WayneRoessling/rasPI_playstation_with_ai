"""Scenario runtime — Scenario definition + state-aware tool dispatcher."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .tools import Tool


@dataclass
class Scenario:
    """One scenario overlay.

    All fields are intentionally simple Python so a scenario can be authored
    inline (like `test_console.py`) or loaded from YAML (Drop 3).
    """
    name: str
    persona_prompt: str
    voice: str = "lessac"
    tools: List[Tool] = field(default_factory=list)
    switch_labels: List[str] = field(
        default_factory=lambda: [f"S{i}" for i in range(1, 11)]
    )
    # 10 friendly names matching SFX slots — for prompt context
    sfx_role_names: List[str] = field(
        default_factory=lambda: [
            "ack", "deny", "caution", "alarm", "arm",
            "disarm", "comms", "click", "tick", "status",
        ]
    )

    def tool_by_name(self, name: str) -> Optional[Tool]:
        return next((t for t in self.tools if t.name == name), None)


class ScenarioRuntime:
    """Glue between a Scenario, the HAL client, and the LLM tool-use loop.

    Responsibilities:
      - tools()         — return Ollama-format tool descriptors
      - build_context() — short system-prompt addendum with current state
      - dispatch_tool() — execute a tool call, enforcing arm-gate
    """

    def __init__(self, hal, scenario: Scenario):
        self.hal = hal
        self.scenario = scenario

    # ── Tools surface ───────────────────────────────────────────────────
    def tools(self) -> list[dict]:
        return [t.descriptor for t in self.scenario.tools]

    def is_armed(self) -> bool:
        return self.hal.state()["key"] == "ARM"

    def dispatch_tool(self, name: str, args: dict) -> str:
        tool = self.scenario.tool_by_name(name)
        if tool is None:
            return f"error: tool {name!r} is not enabled in scenario {self.scenario.name!r}"
        if tool.requires_arm and not self.is_armed():
            # Theatrical: deny SFX + tell the LLM what happened
            try:
                self.hal.play_sfx(2)  # DENY
            except Exception:
                pass
            return f"refused: {name} requires the safety key in ARM (currently SAFE)"
        try:
            result = tool.execute(self.hal, args or {})
            return result if isinstance(result, str) else "ok"
        except Exception as exc:
            return f"error: {exc}"

    # ── Prompt context ──────────────────────────────────────────────────
    def build_context(self) -> str:
        state = self.hal.state()
        lines: list[str] = [f"Scenario: {self.scenario.name}"]
        lines.append(f"Safety key: {state['key']}")

        sw = state["switches"]
        active = [
            (i + 1, self.scenario.switch_labels[i])
            for i in range(min(10, len(sw)))
            if sw[i]
        ]
        if active:
            lines.append("Active switches: " + ", ".join(
                f"S{i} ({n})" for i, n in active))
        else:
            lines.append("Active switches: (none)")

        if state.get("pir"):
            lines.append("PIR motion sensor: triggered")
        if state.get("wake"):
            lines.append(f"Most recent wake word: {state['wake'].get('word')!r}")
        intents = state.get("intents") or []
        if intents:
            keys = ", ".join(i.get("key", "?") for i in intents[-3:])
            lines.append(f"Recent quick-command intents: {keys}")

        return "\n".join(lines)
