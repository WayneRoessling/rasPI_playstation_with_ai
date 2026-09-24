"""Ollama tool-use loop for a single conversational turn.

One call to `run_turn()` handles:
  1. Build system prompt from scenario persona + live hardware context.
  2. POST to /api/chat with the message list + tool descriptors.
  3. If the model returns tool_calls, execute each through the runtime
     (which dispatches to the HAL), append tool-result messages, and
     loop. Otherwise, return the assistant's text.

Recommended models (Ollama tool-use capable):
  - qwen2.5:14b (strong tool calling)
  - llama3.1:8b (good tool calling, lighter)
  - qwen2.5:7b  (smaller but capable)

Models without tool support will return content but no tool_calls — the
loop will exit after one iteration with the model's plain reply.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import requests

log = logging.getLogger("scenario.llm")

OLLAMA_DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:14b"
# How long Ollama keeps the model loaded after a request (its default is 5m,
# after which the next turn pays a full cold load of a ~9GB model).
KEEP_ALIVE = os.environ.get("MINI_AI_KEEP_ALIVE", "30m")

# Cap how many model-tool iterations one turn may take. Generous so simple
# scenarios with 3-4 sequential tool calls don't get truncated.
DEFAULT_MAX_ITERATIONS = 8


def run_turn(
    runtime,
    user_text: str,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_DEFAULT_URL,
    history: Optional[list] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    temperature: float = 0.4,
    on_tool_call=None,
    timeout: float = 180.0,
) -> tuple[str, list]:
    """Run one full conversation turn with tool-use.

    Returns (final_speech, updated_history). `updated_history` excludes
    the system prompt — pass it to the next call as `history=` to keep
    rolling context. The system prompt is rebuilt each turn so it
    reflects live hardware state.

    `on_tool_call(name, args, result)` is an optional observer callback
    fired once per executed tool call.
    """
    system = build_system_prompt(runtime)
    history = list(history or [])
    messages = [{"role": "system", "content": system}] + history + [
        {"role": "user", "content": user_text}
    ]
    tools = runtime.tools()

    final_text = ""
    for iteration in range(max_iterations):
        t0 = time.monotonic()
        resp = _ollama_chat(ollama_url, model, messages, tools,
                            temperature=temperature, timeout=timeout)
        dt = time.monotonic() - t0
        msg = resp.get("message", {}) or {}
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls") or []

        log.info("iter=%d dt=%.2fs tool_calls=%d content_len=%d",
                 iteration, dt, len(tool_calls), len(content))

        if tool_calls:
            # Record the assistant message with its tool calls
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            })
            for tc in tool_calls:
                fn = tc.get("function", {}) or {}
                name = fn.get("name", "")
                args = fn.get("arguments", {}) or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                result = runtime.dispatch_tool(name, args)
                log.info("  call %s(%s) -> %s", name, _short(args), _short(result))
                if on_tool_call is not None:
                    try:
                        on_tool_call(name, args, result)
                    except Exception as e:
                        log.warning("on_tool_call observer raised: %r", e)
                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_name": name,
                })
            continue

        # Final turn — model spoke without further tool calls
        final_text = content.strip()
        messages.append({"role": "assistant", "content": final_text})
        break
    else:
        log.warning("max iterations (%d) hit; returning partial", max_iterations)
        final_text = content.strip() if "content" in dir() else ""

    # Return updated history minus the system prompt (rebuilt each turn)
    return final_text, messages[1:]


def build_system_prompt(runtime) -> str:
    persona = runtime.scenario.persona_prompt.strip()
    ctx = runtime.build_context()
    return (
        f"{persona}\n\n"
        f"CURRENT HARDWARE STATE\n{ctx}\n\n"
        "GUIDELINES\n"
        "- You can call tools to control panel hardware (LEDs, sounds, "
        "displays). Tools execute synchronously; their results are "
        "returned to you before you reply.\n"
        "- Some tools require the safety key in ARM. If a tool returns "
        "'refused', tell the user the safety key is not in ARM and "
        "stop trying that tool.\n"
        "- Keep spoken replies short and in character — aim for one "
        "or two sentences.\n"
        "- Don't restate what each tool did; the panel is doing it visibly."
    )


def _ollama_chat(url, model, messages, tools, *, temperature, timeout):
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": temperature},
    }
    r = requests.post(f"{url}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _short(obj) -> str:
    s = json.dumps(obj, default=str) if not isinstance(obj, str) else obj
    return s if len(s) <= 80 else s[:77] + "..."
