# rasPI PlayStation with AI

A voice-controlled play console powered by a Raspberry Pi 5 running local AI.
You talk to it, it thinks on-device (no cloud), and it answers out loud while
driving a physical panel of switches, lights, displays and sound effects.
Pick a scenario — *Space Command launch center*, *spaceship cockpit*, *pirate
space ship*, *Mars control (normal / disaster)*, *army battle command* — and the
whole console changes character: persona, voice, what the switches mean, what
the lights and screens show.

Internally the project is called **Mini-AI** (`mini-ai`); you'll see that name
in file names, the `~/mini-ai` folder on the Pi and the `MINI_AI_*` settings.

**Status:** the voice assistant and the scenario overlay run today against a
browser-based panel simulator. The physical panel build is in progress (see the
[build manual](docs/user-manuals/README.md)). The Pi platform setup is
[PLAN-MAI-003](active_plans/PLAN-MAI-003_NVMe_Migration_and_Full_Setup.md).

---

## How it works

```
 mic ─► whisper.cpp (speech→text) ─► Ollama LLM ─► Piper (text→speech) ─► speaker
                                        │  ▲
                   webcam (vision) ─────┘  │  tool calls: lights, LCD, sounds…
                                           ▼
                        overlay HAL ── JSON-lines ──► RP2040 panel  or  browser simulator
```

- **Plain voice assistant** (`voice_pipeline.py`, default): listen → transcribe →
  answer → speak. Recording stops when you stop talking, and the answer is spoken
  sentence by sentence while the model is still generating it. Say "what do you
  see" to send a webcam frame to a vision model.
- **Scenario console** (`MINI_AI_OVERLAY=true`): push-to-talk from the panel, and
  the LLM drives the panel through scenario-specific tools. Dangerous actions are
  arm-gated behind the physical key switch. See [`overlay/README.md`](overlay/README.md).

## Hardware

| Item | Notes |
|------|-------|
| Raspberry Pi 5, 16GB | The AI brain |
| NVMe SSD in a USB 3.0 enclosure | Boot + root drive (appears as `/dev/sda`) |
| Official 27W USB-C supply (5.1V/5A) | Lower-rated supplies cause silent SSD I/O failures |
| Logitech C920 (any UVC webcam) | Vision input |
| Yahboom YB-MAE02 mic array + speaker | Voice I/O |
| Adafruit Metro RP2040 + panel parts | Physical console — see the [bill of materials](docs/user-manuals/appendix_A_bill_of_materials.md) |

## Software

| Component | Choice |
|-----------|--------|
| OS | Raspberry Pi OS 64-bit (Bookworm) |
| LLM runtime | [Ollama](https://ollama.com) |
| Models | Presets in [`mini_ai_config.py`](mini_ai_config.py): **tiny** (qwen2.5:0.5b + moondream), **fast** — default (llama3.2:1b + moondream), **smart** (llama3.2:3b + llava:7b). Scenario console: qwen2.5:14b |
| Speech-to-text | [whisper.cpp](https://github.com/ggerganov/whisper.cpp) `base.en` |
| Text-to-speech | [Piper](https://github.com/rhasspy/piper), 8 selectable voices |
| Panel firmware | CircuitPython on the Metro RP2040 |

---

## Quick start

Everything is driven from a workstation (Windows/macOS/Linux) over SSH.

1. **Image the drive** with Raspberry Pi Imager, and in its OS customisation set
   the hostname, user, Wi-Fi and **paste your SSH public key** (baking the key in
   avoids first-boot wiping it). Details: PLAN-MAI-003 phases A–D.
2. **Configure the workstation:**
   ```bash
   pip install -r requirements.txt
   cp .env.example .env      # then set MINI_AI_HOST / MINI_AI_USER / MINI_AI_SSH_KEY
   ```
3. **Run the full setup** (~45–90 min, mostly model downloads):
   ```bash
   python setup_all.py
   ```
   | Phase | What it does |
   |---|---|
   | 2 | OS packages, I2C/SPI, `gpu_mem`, reboot |
   | 3 | Camera check, Python venv, OpenCV |
   | 4 | Ollama + every preset's models + the scenario model |
   | 5 | Audio device check |
   | 6 | whisper.cpp build, Piper + all voices, TTS→STT round trip |
   | 7 | VS Code Remote-SSH settings |
   | 8 | Deploy the app to `~/mini-ai`, install desktop launchers |

   Resume after a failure with `--from N`; redeploy code changes with `--only 8`.
4. **Verify:**
   ```bash
   python test_pi_state.py                                            # 13-point health check
   ssh mini-ai '~/mini-ai/.venv/bin/python ~/mini-ai/test_e2e_pipeline.py'   # TTS→STT→LLM→vision→TTS
   ```
5. **Run it** — double-click **Mini-AI Voice** on the Pi desktop, or:
   ```bash
   ssh mini-ai '~/mini-ai/.venv/bin/python ~/mini-ai/voice_pipeline.py'
   ```

### Try the scenario console without hardware

```bash
pip install -r overlay/sim/requirements.txt -r overlay/pi5_hal/requirements.txt -r overlay/scenario/requirements.txt
cd overlay/sim && uvicorn server:app --port 8765     # open http://localhost:8765/
python -m overlay.scenario.demo --repl                # from the repo root; needs Ollama
```

---

## Repository layout

```
├── voice_pipeline.py        voice assistant (plain + scenario-console modes)
├── mini_ai_panel.py         Tk control panel (live voice/personality/volume)
├── mini_ai_config.py        model presets, voices, personalities, saved choices
├── desktop/                 Pi desktop launchers + model/voice pickers
├── overlay/                 scenario console: HAL protocol, simulator, RP2040
│                            firmware, scenarios, canonical catalog, scene tests
├── setup_all.py             workstation → Pi setup, phases 2-8
├── pi_ssh.py                shared SSH helpers (reads .env)
├── push_key.py              one-time password-based SSH key push (fallback)
├── find_and_push_key.py     find the Pi on the LAN + push key
├── check_state.py           quick Pi diagnostics
├── test_pi_state.py         13-point health check
├── test_e2e_pipeline.py     end-to-end pipeline test (runs on the Pi)
├── tests/                   offline tests (run in CI, no hardware needed)
├── repair_pi_rootfs.sh      WSL2 rootfs repair (SD-card era)
├── active_plans/            PLAN-MAI-003 (current setup plan)
├── archive/                 superseded plans, early design draft, SD-card boot refs
└── docs/
    └── user-manuals/        hardware build manual (chapters, appendices, diagrams)
```

## Configuration

| Setting | Where |
|---|---|
| Pi host, user, SSH key (workstation) | `.env` (`MINI_AI_HOST`, `MINI_AI_USER`, `MINI_AI_SSH_KEY`) |
| Saved preset / voice / personality / volume (Pi) | `~/.config/mini-ai/config.json`, set via the desktop pickers |
| One-off overrides (Pi) | `MINI_AI_PRESET`, `MINI_AI_TEXT_MODEL`, `MINI_AI_VISION_MODEL`, `MINI_AI_VOICE`, `MINI_AI_VOLUME`, `MINI_AI_PERSONALITY` |
| Scenario console (Pi) | `MINI_AI_OVERLAY=true`, `MINI_AI_OVERLAY_SCENARIO`, `MINI_AI_OVERLAY_HAL`, `MINI_AI_OVERLAY_MODEL` |
| Mic sensitivity (Pi) | **Control panel → Mic sensitivity**: Auto or a manual Sensitivity, the Pause that ends an utterance, and a live mic meter. Saved to `config.json`; `MINI_AI_VAD_THRESHOLD` / `MINI_AI_VAD_SILENCE_MS` override |
| Responsiveness (Pi) | `MINI_AI_KEEP_ALIVE` (how long models stay loaded, default `30m`), `MINI_AI_VAD=0` (fixed 10s recording instead of stop-on-silence), `MINI_AI_MAX_UTTERANCE` (default 15s) |

For convenient access, add an `~/.ssh/config` entry on the workstation:

```
Host mini-ai
    HostName <pi-ip-or-hostname>
    User <your-username>
    IdentityFile ~/.ssh/id_ed25519_mini_ai
```

## License

[MIT](LICENSE)
