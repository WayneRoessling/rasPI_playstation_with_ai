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
│   ├── scenarios.yaml              TODO
│   ├── switches.yaml               TODO
│   ├── displays.yaml               TODO
│   ├── leds.yaml                   TODO
│   ├── wake_words.yaml             TODO (Nicla Voice keyword catalog)
│   ├── tools.yaml                  TODO (LLM tool registry + arm-gating)
│   └── hardware_modules.yaml       TODO (physical inventory)
├── narratives/scenarios/           OLENT-style prose narratives
│   ├── space_command_launch/       TODO
│   ├── spaceship_cockpit/          TODO
│   ├── pirate_ship/                TODO
│   ├── mars_control_normal/        TODO
│   ├── mars_control_disaster/      TODO
│   └── army_battle_command/        TODO
├── tools/
│   ├── generate_sfx.py             ✓ procedural WAV generator
│   ├── emit_scenarios.py           TODO (narrative → canonical YAML)
│   └── validate_canonical.py       TODO (cross-ref consistency check)
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
├── pi5_hal/                        TODO (Pi-side HAL client library)
│   └── (to be added in next drop)
└── dev_assets/sfx_preview/         output of tools/generate_sfx.py
```

✓ = present in first drop. TODO = planned next.

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

## "First drop" status

Today you can:

1. **Generate the SFX bank**:
   ```bash
   cd overlay
   python tools/generate_sfx.py        # writes 10 WAVs to dev_assets/sfx_preview/
   ```

2. **Run the simulator**:
   ```bash
   cd overlay/sim
   pip install -r requirements.txt
   uvicorn server:app --port 8765
   # open http://localhost:8765/
   ```

3. **Flash the RP2040** (when ready): see
   [`firmware/rp2040/README.md`](firmware/rp2040/README.md). Without any
   peripherals wired, the firmware will still emit `hello` / `ready` /
   `heartbeat` correctly — useful for protocol smoke-testing.

4. **Connect Pi 5 to either**: the next deliverable is the
   `overlay/pi5_hal/` client library that gives `voice_pipeline.py`
   a clean Python interface (`hal.on_switch`, `hal.set_led`,
   `hal.play_sfx`, etc.) over either the USB CDC link to the
   RP2040 or the WebSocket to the simulator. This will integrate
   with the existing `mini_ai_config.py` / `voice_pipeline.py`
   without disrupting the current voice loop.

## What's NOT in this drop, and where it goes next

| Capability                           | Drop |
|--------------------------------------|------|
| Pi 5 HAL client (`overlay/pi5_hal/`) | 2    |
| Ollama tool-use loop integration     | 2    |
| First scenario narrative (Space Command launch) | 3 |
| Other canonical YAMLs (switches, leds, tools, ...) | 3 |
| `emit_scenarios.py` narrative → YAML  | 3   |
| `validate_canonical.py` cross-refs    | 3   |
| Nicla Voice firmware + keyword model  | 4   |
| Real-HW bring-up (per peripheral)     | 5–9 |
| Scenario authoring for remaining five | 6   |
| Scripted scene validation harness     | 7   |

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
Its analog here is `validate_canonical.py` + the scripted-scene
harness running against the browser simulator.
