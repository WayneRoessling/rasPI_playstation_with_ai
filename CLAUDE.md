# Mini-AI — CLAUDE.md

Project context for Claude Code sessions working in this repo.

---

## Hardware

| Item | Detail |
|------|--------|
| Host | Raspberry Pi 5 16GB RAM |
| Storage | 2TB NVMe SSD in USB 3.0 enclosure (boots as `/dev/sda`, not `nvme0n1`) |
| Camera | Logitech C920 (UVC, plug-and-play) |
| Audio | Yahboom YB-MAE02-V1.0 mic array + speaker |
| Power | Must use 27W USB-C supply (5.1V/5A) — 2.5A supplies cause silent I/O failures |

---

## Pi Access

Connection settings live in `.env` (gitignored; template in `.env.example`):
`MINI_AI_HOST`, `MINI_AI_USER`, `MINI_AI_SSH_KEY`. Machine-specific details
(actual IP, username, SSH alias) go in `CLAUDE.local.md`, which is also gitignored —
this repo is public, so never commit them here.

Quick connect:
```bash
ssh -i ~/.ssh/id_ed25519_mini_ai <user>@<pi-ip>   # or: ssh mini-ai (with an ~/.ssh/config alias)
```

---

## Current Plan

**PLAN-MAI-003** — USB-NVMe Migration & Full Automated Setup (`active_plans/PLAN-MAI-003_NVMe_Migration_and_Full_Setup.md`)

Status: **Active — ready to execute**

Phases:
- A: Bootloader update via SanDisk 64GB (set `BOOT_ORDER=0xf41`)
- B: Image 2TB NVMe with Raspberry Pi Imager (preconfigure SSH key, hostname, Wi-Fi)
- C: Boot Pi from USB-NVMe
- D: First-boot verification (dmesg, dpkg, throttled)
- E: `python setup_all.py` (Phases 2-8, ~45-90 min; phase 8 deploys the app code)

---

## Known Quirks / Gotchas

1. **Root is on `/dev/sda2`** — USB-NVMe appears as `sda`, not `nvme0n1`. Verify with `mount | grep " / "`.
2. **Cloud-init can wipe `~/.ssh/authorized_keys`** — SSH key must be baked into the image via Imager (Phase B), not pushed post-boot.
3. **Undervoltage = silent SSD failures** — always check `vcgencmd get_throttled` (`0x0` = healthy) after boot and after model downloads.
4. **`python3-opencv` from apt causes segfaults** — use `pip install opencv-python-headless` inside the venv instead (handled in `setup_all.py`).
5. **Phase 2 reboot wait** — `setup_all.py` waits 60s after reboot; NVMe boots faster than SD so this should be sufficient.
6. **`gpu_mem=64` persistence** — verify it survives reboot via `/boot/firmware/config.txt`.
7. **Counterfeit 1TB SD card** — discarded. Do not reuse it. Recognized by CID product name `asdfg`.

---

## Pre-flight Code Fixes (already applied 2026-04-07)

| File | Fix |
|------|-----|
| `test_pi_state.py`, `check_state.py` | OpenCV check uses `~/mini-ai/.venv/bin/python` |
| `setup_all.py` | Removed `voice_pipeline.py` gate from phase 6 (app is deployed by phase 8) |
| `setup_all.py` | Added `_repush_key()` after phase 2 reboot |
| `setup_all.py` phase 2 | No `python3-opencv` apt package and no OpenCV gate (OpenCV is pip-installed in phase 3) |

The old standalone `phase2_os_setup.py` was removed; phase 2 lives only in `setup_all.py`.

---

## Model Presets (defined in `mini_ai_config.py`)

| Preset | Text model | Vision model | RAM |
|--------|-----------|--------------|-----|
| `tiny` | qwen2.5:0.5b | moondream | ~2.5GB |
| `fast` *(default)* | llama3.2:1b | moondream | ~3.5GB |
| `smart` | llama3.2:3b | llava:7b | ~7GB |

Persistent choices (preset, voice, personality, volume, mic sensitivity) live at
`~/.config/mini-ai/config.json` on the Pi, set from the desktop pickers and the
control panel. Env vars override the file: `MINI_AI_PRESET`, `MINI_AI_TEXT_MODEL`,
`MINI_AI_VISION_MODEL`, `MINI_AI_VOICE`, `MINI_AI_VOLUME`, `MINI_AI_PERSONALITY`,
`MINI_AI_VAD_THRESHOLD`, `MINI_AI_VAD_SILENCE_MS`. Other runtime knobs:
`MINI_AI_KEEP_ALIVE`, `MINI_AI_VAD`, `MINI_AI_MAX_UTTERANCE`, and the scenario
console's `MINI_AI_OVERLAY*` (see README → Configuration).

The mode (plain assistant or a scenario) is picked live in the control panel's
Mode menu and saved as `scenario` in `config.json`; `MINI_AI_OVERLAY=true|false`
forces it at startup. The scenario console uses `qwen2.5:14b` by default —
expect it to be slow on the Pi's CPU; measure during Phase E and consider a
smaller tool-capable model.

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `setup_all.py` | Full setup Phases 2-8 (`--from N` / `--only N` to resume; `--only 8` redeploys app code) |
| `pi_ssh.py` | Shared SSH helpers used by the workstation scripts (reads `.env`) |
| `test_pi_state.py` | 13-point health check (all phases) |
| `test_e2e_pipeline.py` | E2E pipeline on the Pi: TTS→STT→LLM→Vision→TTS |
| `voice_pipeline.py` | The live voice assistant (plain voice mode + scenario console mode) |
| `mini_ai_panel.py` | Tk control panel: voice, personality, volume, mic sensitivity + meter |
| `mini_ai_config.py` | Presets, voices, personalities, saved settings (`config.json`) |
| `desktop/` | Pi desktop launchers + model/voice pickers (installed by phase 8) |
| `overlay/` | Scenario console: HAL protocol, simulator, RP2040 firmware, scenarios, scene tests — see `overlay/README.md` |
| `push_key.py` | One-time SSH key push (password auth, delete `MINI_AI_PASS` after) |
| `find_and_push_key.py` | Auto-detect Pi IP + push key |
| `check_state.py` | Quick Pi diagnostics |
| `requirements.txt` / `requirements-pi.txt` | Pinned deps: workstation / Pi venv |
| `archive/` | Superseded plans and SD-card-era tools (PLAN-MAI-001/002, `repair_pi_rootfs.sh`) |

## Development

- CI (`.github/workflows/ci.yml`) runs on every PR: ruff, `validate_canonical.py`,
  emitted-YAML sync, `test_ptt_smoke`, scene tests against the simulator (mock
  mode), `tests/test_voice_pipeline.py`, and a pinned-deps import of the setup scripts.
- Run the same locally from the repo root:
  `python -m ruff check .`, `python tests/test_voice_pipeline.py`,
  `python -m overlay.scenario.test_ptt_smoke`, and (with the simulator running)
  `python overlay/tools/run_scenes.py --all --mode mock`.
- The repo is public: keep IPs, usernames and secrets in `.env` / `CLAUDE.local.md`.

---

## Completion Checklist (PLAN-MAI-003)

- [ ] Bootloader updated, `BOOT_ORDER=0xf41`
- [ ] Pi boots from USB-NVMe, `/` on `/dev/sda2`
- [ ] `dmesg` zero filesystem errors
- [ ] `vcgencmd get_throttled` → `0x0`
- [ ] `file /var/lib/dpkg/status` → `ASCII text`
- [ ] `setup_all.py` completes Phases 2-8
- [ ] `test_pi_state.py` → 13/13
- [ ] `test_e2e_pipeline.py` → all 5 stages pass
- [ ] Live voice test: speak → hear response
