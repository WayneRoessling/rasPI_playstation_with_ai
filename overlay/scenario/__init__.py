"""Scenario layer for the mini-ai overlay.

Wraps the HAL client with:
  - Scenario definition (persona, voice, allowed tools, switch labels)
  - ScenarioRuntime that builds an LLM system prompt from live hardware
    state and dispatches LLM tool calls back through the HAL
  - Ollama tool-use loop (llm.py)

Real authored scenarios (Space Command launch, pirate ship, etc.) arrive
in Drop 3 with full narratives. Drop 2 ships only `test_console` — a
synthetic scenario used to verify the full pipeline end-to-end.
"""
from .runtime import Scenario, ScenarioRuntime
from .tools import Tool, GENERIC_TOOLS

__all__ = ["Scenario", "ScenarioRuntime", "Tool", "GENERIC_TOOLS"]
