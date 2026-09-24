# mini-ai overlay subsystem

The **overlay** turns the existing mini-ai voice assistant into a
scenario-driven control panel: a Pi 5 brain talking to a real (or
simulated) physical console of switches, lights, displays, and a
sound module. The user selects a scenario — *Space Command launch
center*, *spaceship cockpit*, *pirate space ship*, *Mars control
center (normal)*, *Mars control center (disaster)*, or *army
command battle center* — and the entire feel of the console
swaps: persona, voice, switch meanings, display content, sound
mappings, LLM tool registry.

This directory contains everything that is *not yet present* in
the upstream mini-ai project: protocol spec, simulator,
firmware skeleton, OLENT-style narrative + canonical catalog, and
tools to keep them in sync.

## Reading order

1. [`docs/HAL_PROTOCOL.md`](docs/HAL_PROTOCOL.md) — JSON-lines wire format that
   Pi 5 uses to talk to either the simulator or the real firmware.
   Read this first; everything else assumes it.
2. [`canonical/sfx_bank.yaml`](canonical/sfx_bank.yaml) — the only canonical
   catalog filled in so far. Defines the 10 universal SFX slots.
3. [`firmware/rp2040/README.md`](firmware/rp2040/README.md) — what's on the
   RP2040, how to flash, how to bring up peripherals one at a time.
4. [`sim/README.md`](sim/README.md) — how to run the browser-based hardware
   simulator. Develop everything here before touching real hardware.

## Folder structure

```
overlay/
├── README.md                       this file
├── docs/
│   └── HAL_PROTOCOL.md             serial / WebSocket protocol spec
├── canonical/                      OLENT-style canonical entity catalog
│   ├── sfx_bank.yaml               ✓ 10 universal CH358 sounds
│   ├── scenarios.yaml              ✓ scenario registry (drop 3)
│   ├── switches.yaml               ✓ 10 toggles + PTT + PIR + MT-301
│   ├── displays.yaml               ✓ 1602 LCD + 2 OLEDs
│   ├── leds.yaml                   ✓ 50 LEDs, group partitioning
│   ├── wake_words.yaml             ✓ Nicla keyword bank
│   ├── tools.yaml                  ✓ LLM tool registry + arm-gating
│   └── hardware_modules.yaml       ✓ physical inventory
├── narratives/scenarios/           OLENT-style prose narratives
│   ├── space_command_launch/       ✓ first authored scenario (drop 3)
│   ├── spaceship_cockpit/          ✓ drop 6
│   ├── pirate_ship/                ✓ drop 6
│   ├── mars_control_normal/        ✓ drop 6
│   ├── mars_control_disaster/      ✓ drop 6
│   └── army_battle_command/        ✓ drop 6
├── tools/
│   ├── generate_sfx.py             ✓ procedural WAV generator
│   ├── emit_scenarios.py           ✓ narrative → emitted scenario YAML
│   ├── validate_canonical.py       ✓ cross-ref consistency check
│   └── run_scenes.py               ✓ scripted scene runner (drop 7)
├── scenes/                         ✓ scripted scene validation harness (drop 7)
│   ├── README.md                   ✓ schema + runner UX
│   └── examples/                   ✓ three example scenes
│       ├── test_console_smoke.yaml
│       ├── space_command_armgate.yaml
│       └── pirate_ship_flavour.yaml
├── firmware/rp2040/                CircuitPython firmware (Adafruit Metro)
│   ├── boot.py                     ✓
│   ├── code.py                     ✓ main loop
│   ├── config.py                   ✓ pin map + enable flags
│   ├── lib/protocol.py             ✓ JSON-lines over USB CDC
│   ├── lib/peripherals.py          ✓ stubs (replace incrementally)
│   └── README.md                   ✓ flashing + bring-up guide
├── sim/                            browser-based hardware simulator
│   ├── server.py                   ✓ FastAPI WebSocket broker
│   ├── static/index.html           ✓ panel UI
│   ├── static/panel.css            ✓
│   ├── static/panel.js             ✓ WebSocket client + renderers
│   ├── requirements.txt            ✓
│   └── README.md                   ✓
├── pi5_hal/                        ✓ Pi-side HAL client (drop 2)
│   ├── client.py                   ✓ HalClient + state mirror + RX thread
│   ├── transport.py                ✓ WebSocket, Serial, Mock transports
│   ├── cli.py                      ✓ `python -m overlay.pi5_hal ...`
│   └── README.md                   ✓
├── scenario/                       ✓ Scenario runtime + Ollama tool-use (drop 2)
│   ├── runtime.py                  ✓ Scenario, ScenarioRuntime, arm-gate
│   ├── tools.py                    ✓ Tool dataclass + 9 generic LLM tools
│   ├── llm.py                      ✓ Ollama /api/chat tool-use loop
│   ├── loader.py                   ✓ build a Scenario from its emitted YAML
│   ├── sequences.py                ✓ cancellable background countdowns/ramps
│   ├── test_console.py             ✓ minimal pipeline-verification scenario
│   ├── demo.py                     ✓ `python -m overlay.scenario.demo`
│   └── README.md                   ✓
└── dev_assets/sfx_preview/         output of tools/generate_sfx.py
```

✓ = present. TODO = planned next.

## Architecture in one diagram

```
                          ┌────────────────────────────────┐
                          │   Pi 5 (AI brain)              │
                          │   voice_pipeline.py            │
                          │   + pi5_hal client library     │
                          └──┬─────────────────────────┬───┘
                             │ USB CDC                 │ USB CDC
                             │ (JSON-lines)            │
                             ▼                         ▼
        ┌────────────────────────────┐    ┌─────────────────────────┐
        │  Metro RP2040              │    │  Arduino Nicla Voice    │
        │  CircuitPython firmware    │    │  (events-only subset)   │
        │  • 10 toggle switches      │    │  • wake-word            │
        │  • PTT, PIR, MT-301 key    │    │  • keyword intents      │
        │  • 50 LEDs (74HC595 chain) │    └─────────────────────────┘
        │  • 1602 LCD (panel A)      │
        │  • 938 OLED   (panel B)    │              ──── OR ────
        │  • STEMMA OLED (master)    │
        │  • CH358D sound module     │    ┌─────────────────────────┐
        │    (10 K-pin NPN drivers)  │    │  Browser simulator      │
        └────────────────────────────┘    │  same JSON-lines proto  │
                                          │  (sim/server.py +       │
                                          │   sim/static/...)       │
                                          └─────────────────────────┘
```

Pi 5 does not know whether it's talking to the firmware or the
simulator. That is the whole point of the protocol layer.

## Status

**Drop 1** (shipped): protocol spec, SFX bank + generator, RP2040
firmware skeleton, browser simulator.

**Drop 2** (shipped): Pi-side HAL client, scenario runtime, Ollama
tool-use loop, end-to-end CLI demo verified against the simulator
with `qwen2.5:14b`.

**Drop 3** (shipped): first authored scenario (Space Command launch
center) with prose narrative + YAML frontmatter, full canonical YAML
catalog set (scenarios, switches, displays, leds, tools, wake_words,
hardware_modules), OLENT-lite emitter (`tools/emit_scenarios.py`),
cross-reference validator (`tools/validate_canonical.py`), and
flag-gated overlay integration in `voice_pipeline.py`
(`MINI_AI_OVERLAY=true`) with PTT-gated recording.

**Drop 6** (shipped): the remaining five authored scenarios —
Spaceship Cockpit, Pirate Space Ship, Mars Control Center (Normal
Operations and Disaster Response twin scenarios), and Army Battle
Command Center — each with a prose narrative, OLENT amendment-discipline
CHANGELOG, emitted YAML, and Python scenario module with 3
scenario-specific tools. Drop 6 also lands two Drop-3 polish items:
**label-aware LED/switch addressing** (the `set_switch_indicator_led`
tool plus an explicit label → switch → LED map in the system prompt
so the LLM can light "Main Bus A" rather than guessing LED ids), and
**true start-on-press / stop-on-release PTT** recording in
`voice_pipeline.py` (replaces the Drop-3 hard-cap `arecord -d MAX_SECS`
pattern with subprocess signal management; `MINI_AI_OVERLAY_PTT_MAX`
stays as a safety cap).

**Drop 7** (shipped): the **scripted scene validation harness**
(`overlay/scenes/`, `overlay/tools/run_scenes.py`). Scene YAML files
describe initial hardware state + a sequence of stimuli (injected
events / utterances) + the expected hardware effects. The runner
drives them against the simulator and asserts pass/fail per step.
Two modes: `mock` (scripted tool calls, no LLM) for CI-friendly
plumbing tests, and `llm` (live Ollama tool-use) for end-to-end
behavioural pinning. Minimal opt-in instrumentation in `pi5_hal/client.py`
records outgoing commands and mirrors LCD line writes so assertions
can inspect what the panel was told to do; nothing in the production
paths reads the new fields. Three example scenes ship:
`test_console_smoke` (plumbing), `space_command_armgate` (arm-gate
behaviour), `pirate_ship_flavour` (in-character tool dispatch). See
[`scenes/README.md`](scenes/README.md) for the schema and runner UX.

Today you can:

1. **Generate the SFX bank**:
   ```bash
   cd overlay
   python tools/generate_sfx.py
   ```

2. **Run the simulator**:
   ```bash
   cd overlay/sim
   pip install -r requirements.txt
   uvicorn server:app --port 8765
   # open http://localhost:8765/
   ```

3. **Drive the panel from Python or the CLI**:
   ```bash
   pip install -r overlay/pi5_hal/requirements.txt
   python -m overlay.pi5_hal led 1 on
   python -m overlay.pi5_hal sfx 7
   python -m overlay.pi5_hal lcd 1 "ALT 12000 OK"
   python -m overlay.pi5_hal state
   ```

4. **Run a single LLM-driven turn** (requires Ollama with a
   tool-capable model — `qwen2.5:14b` recommended):
   ```bash
   pip install -r overlay/scenario/requirements.txt
   python -m overlay.scenario.demo \
       "Turn on LEDs 1 through 5, write SYSTEM ARMED on LCD line 1, and play the status sound."
   # or interactively
   python -m overlay.scenario.demo --repl
   ```

5. **Flash the RP2040** (when ready): see
   [`firmware/rp2040/README.md`](firmware/rp2040/README.md).

## What's NOT yet shipped, and where it goes next

| Capability                           | Drop |
|--------------------------------------|------|
| First scenario narrative (Space Command launch)    | ✓ 3 |
| Other canonical YAMLs (switches, leds, tools, ...) | ✓ 3 |
| `emit_scenarios.py` narrative → YAML               | ✓ 3 |
| `validate_canonical.py` cross-refs                 | ✓ 3 |
| `voice_pipeline.py` integration (PTT-gated, tool-use turn) | ✓ 3 |
| Scenario authoring for remaining five              | ✓ 6 |
| Label-aware switch-indicator LED addressing        | ✓ 6 |
| Start-on-press / stop-on-release PTT recording     | ✓ 6 |
| Scripted scene validation harness                  | ✓ 7 |
| Nicla Voice firmware + keyword model               | 4 |
| Real-HW bring-up (per peripheral)                  | 5–9 |

## OLENT relationship

This subsystem applies the **narrative-first** + **canonical entity
catalog** parts of the OLENT method (see workspace
`olent-narratives/`, `olent-method/`) at a project-internal scale.

We do **not** depend on `olent-method` as a package — its method
engine is still in skeleton state. Instead, `tools/emit_scenarios.py`
(to come) will be a lean ~200-line emitter implementing the same
pattern: prose narrative → canonical YAML → cross-ref validation,
with `CHANGELOG.md` amendment discipline per scenario.

Walkthrough-capture (the Playwright UI pipeline in
`olent-walkthrough-capture/`) doesn't apply — there's no web UI.
Its analog here is `validate_canonical.py` (static cross-reference
check, drop 3) + the scripted-scene harness in `scenes/` (dynamic
behavioural check, drop 7) — both running against the browser
simulator.
