# scenario — Ollama tool-use + scenario runtime

Wraps `pi5_hal` with the **scenario layer**: an LLM (via Ollama) that
sees live hardware state in its system prompt and controls the panel
by calling typed tools. Each scenario picks which tools the LLM may
call and how the panel is "labelled" (switch meanings, persona, voice).

```
┌────────────────┐    JSON-lines     ┌──────────────┐
│  ScenarioRuntime│ ◄───── HAL ─────► │  Sim or HW   │
│  + Ollama loop  │                   │  controller  │
└────────────────┘                   └──────────────┘
        ▲
        │ tool calls
        │
   ┌─────────┐
   │ Ollama  │ qwen2.5:14b / llama3.1:8b — must be tool-capable
   └─────────┘
```

## Quickstart

1. Start the sim (one terminal):
   ```bash
   cd overlay/sim
   uvicorn server:app --port 8765
   ```
   Open `http://localhost:8765/` so you can watch the panel.

2. Make sure Ollama is up and has a tool-capable model:
   ```bash
   ollama list      # need e.g. qwen2.5:14b or llama3.1:8b
   ```

3. Fire one demo turn:
   ```bash
   python -m overlay.scenario.demo \
       "Turn on LEDs 1 through 5, write SYSTEM ARMED on LCD line 1, and play the status sound."
   ```

   You should see in the sim:
   - LEDs 1–5 light up
   - LCD line 1 shows `SYSTEM ARMED`
   - SFX slot K10 (STATUS) flashes

4. Or run interactively:
   ```bash
   python -m overlay.scenario.demo --repl
   > set up a launch readiness check
   > now turn it all off
   ```

## Authoring a scenario

A `Scenario` is a plain dataclass:

```python
from overlay.scenario import Scenario
from overlay.scenario.tools import GENERIC_TOOLS

MY_SCENARIO = Scenario(
    name="Space Command Launch",
    voice="ryan",
    persona_prompt="You are Mission Control at Space Command. ...",
    tools=list(GENERIC_TOOLS),
    switch_labels=[
        "Ignition Arm", "Boost Stage", "Telemetry", "Range Safety",
        "Main Bus A",  "Main Bus B",   "Comms",     "Beacon",
        "Hold",        "Abort",
    ],
)
```

Per-scenario tools (with `requires_arm=True` for destructive actions)
are added by constructing additional `Tool` instances. See
`test_console.py` for an example (`trigger_emergency_alarm`).

Drop 3 will move scenario definitions to YAML emitted from prose
narratives in `overlay/narratives/scenarios/<name>/narrative.md`,
following the OLENT narrative-first pattern.

## Arm-gate

Tools marked `requires_arm=True` are refused unless the MT-301 key
switch is in `ARM`. On refusal, the runtime:
1. Plays SFX slot 2 (DENY) for an audible cue.
2. Returns `"refused: <tool> requires the safety key in ARM (currently SAFE)"`
   to the LLM, which is instructed to relay this to the user and not retry.

To test the arm-gate locally:
```bash
python -m overlay.scenario.demo "trigger the emergency alarm now"
# in the sim, change the key dropdown to ARM, then repeat.
```

## Running the loop without the demo wrapper

```python
from overlay.pi5_hal import HalClient, WebsocketTransport
from overlay.scenario import ScenarioRuntime
from overlay.scenario.test_console import TEST_CONSOLE
from overlay.scenario.llm import run_turn

with HalClient(WebsocketTransport("ws://127.0.0.1:8765/hal")) as hal:
    rt = ScenarioRuntime(hal, TEST_CONSOLE)
    speech, history = run_turn(rt, "blink LED 10 by toggling it twice")
    print(speech)
```

## Where this fits in the voice pipeline

Drop 2 ships the **runtime** and the **tool-use loop** — both fully
testable from the CLI. Drop 3 wires them into `voice_pipeline.py`:

```python
# pseudocode for Drop 3
while running:
    audio = record_until_ptt_release()
    text = whisper(audio)
    speech, history = run_turn(runtime, text, history=history)
    piper_say(speech)
```

The existing `voice_pipeline.py` keeps working as a non-overlay
fallback for users without the hardware/sim.

## Requirements

```
requests>=2.31
```
(`websocket-client` is brought in transitively by `pi5_hal`.)

The default model is `qwen2.5:14b`. Override per-call with
`run_turn(..., model="llama3.1:8b")` or via the demo's `--model` flag.
