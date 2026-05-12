# overlay/scenes — Scripted Scene Validation Harness (Drop 7)

The scene harness is the **behavioural complement** to
`overlay/tools/validate_canonical.py`. Where the canonical validator
proves the YAML catalogs are internally consistent, the scene harness
proves a scenario *actually does what the narrative says it does*
when an utterance arrives — switches gate the right tools, the LLM
picks the in-character action, the arm-gate refuses what it should,
LEDs and the LCD end up in the expected state.

This is the single-device analog of the OLENT walkthrough-capture
Playwright pipeline: a way to drive scenarios through expected I/O
sequences and assert results, so future scenario edits don't silently
break.

## Quickstart

The simulator must be running for the harness to do anything — it
opens both a `HalClient` and an event injector against the sim
WebSocket. Ollama is only needed in LLM mode.

```bash
# 1. terminal A — simulator (one-time)
cd overlay/sim && uvicorn server:app --port 8765

# 2. terminal B — run all example scenes in mock mode (CI-friendly)
python overlay/tools/run_scenes.py --all --mode mock

# 3. terminal B — run the same scenes through Ollama (slower; ~minutes)
python overlay/tools/run_scenes.py --all
```

A single scene file can be run on its own:

```bash
python overlay/tools/run_scenes.py overlay/scenes/examples/space_command_armgate.yaml
python overlay/tools/run_scenes.py overlay/scenes/examples/space_command_armgate.yaml -v
```

`-v / --verbose` prints every step, every tool call dispatched, and
the assistant reply (if any). `--json` emits a machine-readable
summary on stdout for future CI integration. Exit code is **0** when
every scene passes, **1** on any test failure, **2** on YAML/schema
load errors.

## Modes

| `--mode` / scene `mode:` | Behaviour                                                                                        | Speed       | Needs |
|--------------------------|--------------------------------------------------------------------------------------------------|-------------|-------|
| `mock` (default for the smoke scene) | Each utterance's `scripted_tool_calls` block is dispatched directly through `ScenarioRuntime`. Arm-gate, refusal, and tool errors all execute exactly as in production. | Subsecond per step (plus any `time.sleep` in scenario tools). | Sim only. |
| `llm` (default for the others)       | Each utterance is sent through `scenario.llm.run_turn()` with the configured Ollama model. Tools the LLM calls are dispatched; the observer records `(name, args, result)` triples. | Several seconds per utterance; whole-scene runs are minutes. | Sim + Ollama. |

`--mode mock` and `--mode llm` on the CLI **override** every scene's
declared mode. If a scene declares `mode: llm` and you pass
`--mode mock`, the runner will use the `scripted_tool_calls` block
instead of calling Ollama.

The three example scenes include both blocks so they pass in either
mode, but most real-world scenes will pick one and stick with it.

## Scene YAML schema

```yaml
name: "human-readable test case name"        # required
scenario: space_command_launch                # required; must exist in
                                              # overlay/scenario/demo.py SCENARIOS
mode: llm                                     # "llm" | "mock"; default "llm"
model: qwen2.5:14b                            # optional; LLM mode only

# Initial panel state. Applied by the runner via injected `key` and
# `switch` events before the first step. Only deltas are sent — if the
# scene wants the panel to start at all-zero/SAFE, the setup can be
# omitted entirely.
setup:
  key: SAFE                                   # SAFE | ARM | OFF | RUN | TEST
  switches: {1: on, 2: off, 3: on, 4: off, 5: off,
             6: off, 7: off, 8: off, 9: off, 10: off}
  ptt: off                                    # optional
  pir: off                                    # optional

steps:
  - <step-1>
  - <step-2>
  ...

# Mock mode only — maps each utterance string to the tool calls the
# mock LLM should emit. Keys must match `steps[i].utterance` exactly.
scripted_tool_calls:
  "begin launch sequence":
    - {name: initiate_launch_sequence}
  "clear the panel":
    - {name: clear_leds}
    - {name: clear_lcd}

# Optional: scripted reply text for mock mode, used by reply_matches
# assertions. LLM mode ignores this; the real model reply is matched.
scripted_replies:
  "begin launch sequence": "Roger, ignition in ten."
```

### Step kinds

Every step must declare **exactly one** of: `event`, `utterance`,
`wait`, `assert`. An optional `expect` block holds assertions
evaluated after the stimulus.

| Step           | Payload                                            | What happens                                                                                                   |
|----------------|----------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `event`        | `{t: switch\|ptt\|pir\|key\|wake\|intent, ...}`    | The runner injects the frame via its own WebSocket connection. The sim broadcasts; the HAL state mirror picks it up. Mirrors the on-wire format in `overlay/docs/HAL_PROTOCOL.md §4`. |
| `utterance`    | `"<user text>"`                                    | Mock mode: dispatch each entry in `scripted_tool_calls[utterance]` through `ScenarioRuntime`. LLM mode: send through `scenario.llm.run_turn()` and let the model decide what to call. |
| `wait`         | integer milliseconds                               | Pure sleep. Useful between two stimuli where the second depends on the first having settled (SFX, sequenced LED animations). |
| `assert`       | (no payload)                                       | Evaluate `expect` only — no stimulus. Useful as a setup sanity check before driving anything.                  |

### Assertion checks

All assertions are evaluated *after* the step's stimulus completes,
against the HAL state mirror + the commands the runtime issued during
this step. They're all optional.

| Assertion             | Type        | Passes when …                                                                                              |
|-----------------------|-------------|------------------------------------------------------------------------------------------------------------|
| `tool_calls_include`  | list of patterns | Every pattern matches at least one tool call dispatched during this step.                              |
| `tool_calls_exclude`  | list of patterns | None of the patterns matches any dispatched tool call.                                                 |
| `tool_call_count`     | int         | The total number of tool calls in this step equals this exactly.                                            |
| `reply_matches`       | regex       | The assistant reply matches the pattern (case-insensitive flags via `(?i)`). LLM mode: real reply. Mock mode: from `scripted_replies`. |
| `leds_on`             | list[int]   | Exactly these LED ids (1..50) are lit. Whole-panel match.                                                  |
| `leds_changed`        | list[int]   | The set of LEDs that changed state during this step is exactly this list. `[]` means "no LED changes".     |
| `lcd_line_1`          | string      | Line 1 of the 1602 LCD's last-commanded content equals this exactly.                                       |
| `lcd_line_2`          | string      | Line 2 same.                                                                                                |
| `state.<dot.path>`    | any         | A dot-resolved path into `hal.state()` equals the given value. E.g. `state.key: ARM`, `state.switches.0: 1`. |

A tool-call **pattern** is:

```yaml
- name: initiate_launch_sequence
  args_contain: {slot: 2}          # optional — every key here must equal the actual arg
  result_matches: "ok: launch"     # optional — regex on the runtime's tool-result string
```

`args_contain` is a subset check; the actual call may have extra args.
`result_matches` is how to assert on arm-gate refusals
(`result_matches: "refused"`), since the runtime turns those into
string returns rather than raising.

## YAML 1.1 gotcha — bare `on`/`off`

PyYAML's safe_load follows YAML 1.1, which coerces the unquoted words
`on`, `off`, `yes`, `no` (case-insensitive) into booleans. That means:

| Written                                 | Parsed as                              |
|-----------------------------------------|----------------------------------------|
| `{id: 1, on: true}`                     | `{"id": 1, True: True}`  ← key is True |
| `{id: 1, "on": true}`                   | `{"id": 1, "on": True}`  ← correct     |
| `switches: {1: on}`                     | `{1: True}`                            |

The runner is tolerant of the second form for setup values (the
`_to_bool` helper accepts booleans). But when a **key** is `on`
(typically in `scripted_tool_calls[...].args` or in
`tool_calls_include[].args_contain`), you must quote it — otherwise
the key becomes the boolean `True` and the dispatcher won't see it.

The example scenes use the quoted form `"on": true` everywhere.

## Event injection — how the runner reaches the HAL

The runner opens **two** WebSocket connections to the simulator:

1. **HalClient** — the same `HalClient` the scenario uses in
   production. Its rx loop maintains the state mirror that the
   harness reads for `leds_*`, `lcd_line_*`, and `state.*` assertions.
2. **Injector** — a separate raw WebSocket connection used only to
   send `switch`/`key`/`ptt`/`pir`/`wake`/`intent` frames. The sim
   broadcasts every frame to every **other** client, so frames sent by
   the injector arrive at the HalClient just as if they had originated
   in the browser UI.

This split exists so the injector's writes don't echo back through
the HalClient's own send path (which would update mirror but skip the
event dispatcher).

## Adding a new scene

1. Drop a new `*.yaml` in `overlay/scenes/examples/`.
2. Pick the scenario id from the registry in `overlay/scenario/demo.py`.
3. Decide the mode. If the scene needs to run in CI, prefer `mock` and
   author the `scripted_tool_calls` block. If you specifically want to
   pin LLM behaviour (persona regex, expected tool-pick), prefer
   `llm`. If the scene must pass in both modes, include both blocks.
4. Run it locally with `python overlay/tools/run_scenes.py
   path/to/scene.yaml -v` and iterate the assertions until they
   reflect the actual observed behaviour.

The scenes directory only autoloads from `overlay/scenes/examples/`
under `--all`; subdirectories you want CI to skip can live elsewhere.

## Caveats

* The harness assumes the simulator at `--sim` is up; it does **not**
  start one. The error message on connection failure includes the URL.
* Each scene runs back-to-back without restarting the sim, but each
  scene calls `hal.reset()` + `clear_leds()` + `clear_lcd()` before
  applying its `setup`. If a scenario tool has process-global state
  (e.g. the Pirate Ship `itertools.cycle` rotation), that state still
  persists between scenes — by design, since it's how the scenario
  works in production.
* Scenes that exercise `initiate_launch_sequence` take ~10 s per
  attempt: the tool runs a real `time.sleep(1.0)` per tick. Budget
  accordingly under `--all`.
* LLM mode has no per-step retry. A flaky model response (rare with
  qwen2.5:14b on these scenes) results in a scene-level FAIL.
