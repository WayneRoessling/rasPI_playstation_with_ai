"""End-to-end Drop-2 demo: HAL + Ollama tool-use against the simulator.

Connects to the running browser simulator, builds a `ScenarioRuntime`
around the `test_console` scenario, sends one user utterance through the
Ollama tool-use loop, and prints the final assistant speech. Tool calls
fire against the panel in real time — you'll see LEDs change, displays
update, and SFX trigger in the simulator browser tab.

Run the sim first:
    cd overlay/sim
    uvicorn server:app --port 8765

Then in another shell:
    python -m overlay.scenario.demo \\
        "Turn on LEDs 1 through 5, write 'SYSTEM ARMED' on LCD line 1, " \\
        "and play the status sound."

Or interactively:
    python -m overlay.scenario.demo --repl
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

# Support both `python -m overlay.scenario.demo` (relative imports work)
# and `python overlay/scenario/demo.py` (fall back to absolute).
try:
    from ..pi5_hal.client import HalClient
    from ..pi5_hal.transport import WebsocketTransport
    from .runtime import ScenarioRuntime
    from .test_console import TEST_CONSOLE
    from .space_command_launch import SPACE_COMMAND_LAUNCH
    from .spaceship_cockpit import SPACESHIP_COCKPIT
    from .pirate_ship import PIRATE_SHIP
    from .mars_control_normal import MARS_CONTROL_NORMAL
    from .mars_control_disaster import MARS_CONTROL_DISASTER
    from .army_battle_command import ARMY_BATTLE_COMMAND
    from .llm import run_turn, DEFAULT_MODEL, OLLAMA_DEFAULT_URL
except ImportError:
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from overlay.pi5_hal.client import HalClient  # type: ignore
    from overlay.pi5_hal.transport import WebsocketTransport  # type: ignore
    from overlay.scenario.runtime import ScenarioRuntime  # type: ignore
    from overlay.scenario.test_console import TEST_CONSOLE  # type: ignore
    from overlay.scenario.space_command_launch import SPACE_COMMAND_LAUNCH  # type: ignore
    from overlay.scenario.spaceship_cockpit import SPACESHIP_COCKPIT  # type: ignore
    from overlay.scenario.pirate_ship import PIRATE_SHIP  # type: ignore
    from overlay.scenario.mars_control_normal import MARS_CONTROL_NORMAL  # type: ignore
    from overlay.scenario.mars_control_disaster import MARS_CONTROL_DISASTER  # type: ignore
    from overlay.scenario.army_battle_command import ARMY_BATTLE_COMMAND  # type: ignore
    from overlay.scenario.llm import run_turn, DEFAULT_MODEL, OLLAMA_DEFAULT_URL  # type: ignore


# Scenario id → Scenario instance. Add new authored scenarios here as
# they ship — the registry is intentionally small and explicit.
SCENARIOS = {
    "test_console": TEST_CONSOLE,
    "space_command_launch": SPACE_COMMAND_LAUNCH,
    "spaceship_cockpit": SPACESHIP_COCKPIT,
    "pirate_ship": PIRATE_SHIP,
    "mars_control_normal": MARS_CONTROL_NORMAL,
    "mars_control_disaster": MARS_CONTROL_DISASTER,
    "army_battle_command": ARMY_BATTLE_COMMAND,
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("text", nargs="?", default=None,
                    help="user utterance (omit with --repl for interactive)")
    ap.add_argument("--repl", action="store_true",
                    help="interactive prompt loop (Ctrl-C to exit)")
    ap.add_argument("--sim", default="ws://127.0.0.1:8765/hal",
                    help="simulator WebSocket URL")
    ap.add_argument("--scenario", default="test_console",
                    choices=sorted(SCENARIOS.keys()),
                    help="scenario id to load (default: test_console)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="Ollama model name")
    ap.add_argument("--ollama", default=OLLAMA_DEFAULT_URL,
                    help="Ollama base URL")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    if not args.repl and not args.text:
        ap.error("provide a user utterance or pass --repl")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
    )

    hal = HalClient(WebsocketTransport(args.sim))
    scenario = SCENARIOS[args.scenario]
    print(f"[demo] connecting to {args.sim} ...", file=sys.stderr)
    print(f"[demo] scenario: {args.scenario} ({scenario.name})", file=sys.stderr)
    hal.connect()
    runtime = ScenarioRuntime(hal, scenario)

    def observer(name, kwargs, result):
        print(f"   ▸ tool {name}({_short(kwargs)}) -> {result}", file=sys.stderr)

    history: list = []
    try:
        if args.text:
            history = _one(runtime, args.text, args, observer, history)
        if args.repl:
            print("[demo] interactive mode. type a request, blank line to exit.",
                  file=sys.stderr)
            while True:
                try:
                    line = input("> ").strip()
                except EOFError:
                    break
                if not line:
                    break
                history = _one(runtime, line, args, observer, history)
    finally:
        hal.disconnect()


def _one(runtime, user_text, args, observer, history):
    print(f"\n[user] {user_text}\n", file=sys.stderr)
    t0 = time.monotonic()
    speech, history = run_turn(
        runtime, user_text,
        model=args.model,
        ollama_url=args.ollama,
        history=history,
        on_tool_call=observer,
    )
    dt = time.monotonic() - t0
    print(f"\n[assistant] ({dt:.1f}s) {speech}\n", file=sys.stderr)
    return history


def _short(obj):
    import json
    s = json.dumps(obj, default=str)
    return s if len(s) <= 60 else s[:57] + "..."


if __name__ == "__main__":
    main()
