# Mini-AI — Raspberry Pi 5 Edge AI Platform

**Project Code:** Mini-AI
**Status:** Active — Ready to execute PLAN-MAI-003 (1TB SD card was counterfeit)
**Hardware:** Raspberry Pi 5 (16GB RAM) + 2TB USB-NVMe SSD
**Goal:** Edge voice-assistant + vision AI node with local LLM inference

---

## Project Scope

Build a fully offline, on-device AI assistant platform on a Raspberry Pi 5 that combines:
- **Voice I/O** — Yahboom YB-MAE02-V1.0 microphone array + speaker module
- **Vision** — Logitech USB webcam (UVC, plug-and-play)
- **LLM Inference** — Local quantized multimodal model (vision + language)
- **Speech Pipeline** — Whisper STT → LLM → Piper TTS
- **Developer Access** — VSCode Remote SSH from Windows workstation

---

## Quick Start

```bash
# 1. Install dependencies (on Windows workstation)
pip install -r requirements.txt

# 2. Create .env from template
cp .env.example .env
# Edit .env with your Pi IP, username, and SSH key path

# 3. Flash Pi with Bookworm Lite 64-bit, boot, wait 2 min

# 4. Push SSH key (first time only — will prompt for password)
python push_key.py

# 5. Run full setup (Phases 2-7, ~1-2 hours)
python setup_all.py

# 6. Health check
python test_pi_state.py
```

### Resume after failure

```bash
python setup_all.py --from 4    # resume from phase 4
python setup_all.py --only 6    # re-run only phase 6
```

### After reflash

If you need to reflash the SD card, the full setup can be re-run from scratch:
```bash
python push_key.py              # push SSH key to fresh Pi
python setup_all.py             # runs all phases 2-7
python test_pi_state.py         # verify everything
```

---

## Directory Structure

```
Mini-AI/
├── README.md                  ← This file
├── .env.example               ← Config template (copy to .env)
├── .gitignore
├── requirements.txt           ← Python dependencies (paramiko)
├── pi_ssh.py                  ← Shared SSH helpers (config, connect, run, gate)
├── push_key.py                ← One-time SSH key deployment
├── find_and_push_key.py       ← Auto-detect Pi IP + push key
├── setup_all.py               ← Full setup: Phases 2-7 in one script
├── check_state.py             ← Quick Pi diagnostics
├── test_pi_state.py           ← Comprehensive health check (all phases)
├── test_e2e_pipeline.py       ← E2E pipeline test (TTS→STT→LLM→Vision→TTS)
├── voice_pipeline.py          ← The voice assistant application
├── phase2_os_setup.py         ← Phase 2 standalone (used by setup_all.py)
├── repair_pi_rootfs.sh        ← WSL2-based rootfs repair for corrupted cards
├── active_plans/
│   └── PLAN-MAI-001_Pi5_Platform_Build.md
├── designs/
│   └── DESIGN-MAI-001_System_Architecture.md
└── docs/reference/
    ├── cmdline_normal.txt     ← Kernel boot params (normal mode)
    └── cmdline_recovery.txt   ← Kernel boot params (recovery mode)
```

---

## Hardware Inventory

| Item | Spec | Status |
|------|------|--------|
| Raspberry Pi 5 | 16GB RAM variant | Acquired |
| microSD (boot) | 1TB (new) — replaces 64GB OEM card | Acquired |
| Camera | Logitech USB webcam (UVC class) | Acquired |
| Voice module | Yahboom YB-MAE02-V1.0 (mic array + speaker) | Acquired |
| Network | Ethernet (setup) → Wi-Fi (production) | — |

---

## Key Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| OS | Raspberry Pi OS Bookworm Lite 64-bit | Lightweight, Pi-optimized, libcamera native |
| LLM Runtime | Ollama (llama.cpp backend) | Easiest lifecycle management, GGUF support |
| Vision+Language Model | LLaVA 1.6 7B (Q4_K_M) | Best vision+text balance for 16GB |
| Fast Text Model | Llama 3.2 3B | Sub-second voice responses |
| Speech-to-Text | Whisper.cpp (base.en or small.en) | Fastest Pi-optimized STT |
| Text-to-Speech | Piper-TTS | Real-time, offline, high quality |
| Dev Environment | VSCode Remote SSH | Native on-device editing from Windows |

---

## Active Plans

| Plan | Title | Status |
|------|-------|--------|
| [PLAN-MAI-001](active_plans/PLAN-MAI-001_Pi5_Platform_Build.md) | Pi 5 Platform Build | Reference |
| [PLAN-MAI-002](active_plans/PLAN-MAI-002_Reflash_and_Full_Setup.md) | Reflash & Full Setup | Abandoned (counterfeit SD card) |
| [PLAN-MAI-003](active_plans/PLAN-MAI-003_NVMe_Migration_and_Full_Setup.md) | USB-NVMe Migration & Full Setup | Active — ready to execute |

---

## SSH Access

```bash
# After initial setup (replace <pi-ip> with the Pi's IP)
ssh miniai_admin@<pi-ip>

# Or using .ssh/config entry (see PLAN-MAI-001 Phase 7)
ssh mini-ai
```
