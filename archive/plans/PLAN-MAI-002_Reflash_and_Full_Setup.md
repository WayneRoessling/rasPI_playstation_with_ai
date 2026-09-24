> **ARCHIVED.** Abandoned when the 1TB SD card proved counterfeit; superseded by
> [PLAN-MAI-003](../../active_plans/PLAN-MAI-003_NVMe_Migration_and_Full_Setup.md).
> Kept for the incident history.

# PLAN-MAI-002 — Reflash SD Card & Full Automated Setup

**Plan:** PLAN-MAI-002
**Project:** Mini-AI
**Status:** ABANDONED — SD card confirmed counterfeit (2026-04-07)
**Created:** 2026-04-06
**Closed:** 2026-04-07
**Supersedes:** Manual execution of PLAN-MAI-001 Phases 2-7
**Superseded by:** PLAN-MAI-003 (NVMe SSD migration)

---

## Background

During the initial build (PLAN-MAI-001), the 1TB microSD card developed active filesystem corruption. Symptoms observed:

- dpkg status file detected as "DOS executable" instead of text
- 41 `/var/lib/dpkg/info/*.list` files corrupted (binary garbage)
- EXT4 `Structure needs cleaning` errors on `rm` operations
- Freshly built binaries (cmake, whisper-cli) corrupted within minutes
- `OSError: [Errno 74] Bad message` on dist-info directories

**Root cause:** SD card hardware failure (bad sectors or failing controller). The original card corruption incident from the interrupted apt upgrade likely caused initial damage, and the card has been degrading since.

**Decision:** Reflash the card and re-run all setup phases using the automated `setup_all.py` script.

---

## What Was Verified Before Corruption Spread

All components were individually confirmed working on the Pi before filesystem corruption made them unusable:

| Component | Verified | Notes |
|-----------|----------|-------|
| SSH key auth | Yes | Paramiko Ed25519 connection stable |
| OS packages (git, ffmpeg, cmake, etc.) | Yes | All installed via apt |
| I2C / SPI / gpu_mem=64 | Yes | Enabled and confirmed |
| Logitech C920 USB camera | Yes | Detected at `/dev/video0`, OpenCV captured 1920x1080 |
| OpenCV 4.13.0 (pip) | Yes | `import cv2` works, camera capture works |
| Ollama v0.20.2 | Yes | Installed via patched script (curl wrapper for wlan0) |
| Llama 3.2 3B | Yes | "Four" response to "What is 2+2?" — 5.7s |
| LLaVA 7B (Q4_0) | Yes | "A well-stocked office bookshelf..." — 183s (cold start) |
| Whisper.cpp base.en | Yes | "Hello, this is a test of the speech pipeline." — 2.1s |
| Piper TTS lessac-medium | Yes | Generated 38KB WAV from "hello world" — 2.8s |
| ALSA playback (USB Audio, card 2) | Yes | YB-MAE02 detected |
| ALSA capture (USB Audio + C920 mic) | Yes | Both cards detected |

---

## Pre-Reflash Checklist

Before reflashing, verify nothing needs to be saved from the Pi:

- [x] `voice_pipeline.py` — saved in repo
- [x] `test_e2e_pipeline.py` — saved in repo
- [x] All setup scripts — saved in repo
- [x] SSH keys — on Windows workstation (`~/.ssh/id_ed25519_mini_ai`)
- [x] No unique data on Pi (all code lives in this repo)
- [ ] Ollama models will need re-download (~6.5GB, 30-60 min)
- [ ] Whisper.cpp will need rebuild (~5 min compile)

---

## Reflash Procedure

### Step 1 — Flash the Card

1. Power off the Pi, remove the 1TB microSD
2. Insert into Windows PC card reader
3. Launch Raspberry Pi Imager:
   - Device: Raspberry Pi 5
   - OS: Raspberry Pi OS Lite (64-bit) — Bookworm
   - Storage: 1TB microSD
4. Edit Settings:
   - Hostname: `mini-ai-01`
   - Username: `<your-username>`
   - Password: *(Pi admin password from your password manager; setup scripts read it from `.env` via `MINI_AI_PASS`)*
   - Wi-Fi: configured (SSID + password + country US)
   - SSH: enabled with password auth
5. Write + Verify (30-60 min — do not interrupt)
6. Eject card safely

### Step 2 — First Boot

1. Insert card into Pi
2. Connect Ethernet cable
3. Plug in USB-C power
4. Wait 2 full minutes for first-boot expansion

### Step 3 — Push SSH Key

```bash
cd rasPI_playstation_with_ai   # your clone of this repo
python push_key.py
```

If the Pi IP changed, update `.env` first, or use:
```bash
python find_and_push_key.py
```

### Step 4 — Run Full Setup

```bash
python setup_all.py
```

This runs Phases 2-7 automatically:

| Phase | What | Duration | Key Actions |
|-------|------|----------|-------------|
| 2 | OS Setup | 10-20 min | apt packages, I2C/SPI, gpu_mem=64, reboot |
| 3 | Camera | 5 min | OpenCV in venv, capture test image from C920 |
| 4 | LLM | 30-60 min | Install Ollama, pull llama3.2:3b + llava:7b |
| 5 | Audio | 1 min | Verify ALSA playback + capture devices |
| 6 | Pipeline | 15-30 min | Build whisper.cpp, install Piper TTS, round-trip test |
| 7 | VSCode | 1 min | Workspace settings, requirements.txt |

**Network note:** The Ethernet gateway (<gateway>) blocks ollama.com and github.com. The setup script automatically swaps the default route to Wi-Fi (10.1.10.1) for those downloads, then restores Ethernet afterward.

### Step 5 — Verify

```bash
python test_pi_state.py
```

Expected: 13/13 checks pass.

### Step 6 — Deploy Pipeline

```bash
scp -i ~/.ssh/id_ed25519_mini_ai voice_pipeline.py <user>@<pi-ip>:~/mini-ai/
scp -i ~/.ssh/id_ed25519_mini_ai test_e2e_pipeline.py <user>@<pi-ip>:/tmp/
```

### Step 7 — E2E Test

```bash
ssh -i ~/.ssh/id_ed25519_mini_ai <user>@<pi-ip> \
  '~/mini-ai/.venv/bin/python /tmp/test_e2e_pipeline.py'
```

Expected: All 5 stages pass (TTS, STT, LLM text, LLM vision, TTS response).

---

## Resume After Failure

If `setup_all.py` fails at any phase:

```bash
python setup_all.py --from <phase>     # resume from failed phase
python setup_all.py --only <phase>     # re-run one phase
```

---

## Known Issues & Mitigations

| Issue | Mitigation |
|-------|-----------|
| Ethernet blocks ollama.com/github.com | Script auto-routes through Wi-Fi |
| LLaVA 7B digest mismatch on first pull | Script retries automatically via Ollama |
| First LLM inference slow (cold start) | Normal — model loading takes 2-10s, subsequent calls fast |
| LLaVA vision garbage output when RAM full | Unload models before vision test: `keep_alive: 0` |
| System python3-opencv segfaults (dpkg corruption) | Using pip opencv-python-headless in venv instead |
| Piper binary corrupt in .local/bin | Using venv-installed piper instead |

---

## Estimated Total Time

| Step | Duration |
|------|----------|
| Flash + first boot | 45-90 min |
| Push SSH key | 1 min |
| `setup_all.py` (Phases 2-7) | 60-120 min |
| Health check + E2E test | 5 min |
| **Total** | **~2-3.5 hours** |

---

## Completion Criteria

- [ ] Fresh Bookworm Lite on 1TB card, Pi booting cleanly
- [ ] `python test_pi_state.py` — 13/13 checks pass
- [ ] `test_e2e_pipeline.py` — all 5 stages pass
- [ ] VSCode Remote-SSH connects and opens ~/mini-ai
- [ ] Live voice pipeline test: speak → hear response

---

## POST-MORTEM (2026-04-07) — Plan Abandoned

The reflash was performed and `setup_all.py` was attempted. It failed identically to the previous attempt within the first 30 minutes. Investigation found the **SD card itself is counterfeit/defective**, not a software issue.

### Symptoms reproduced after reflash
- `/var/lib/dpkg/status` corrupted to binary garbage (`file` reports `data`, not `ASCII text`)
- `/var/lib/dpkg/status-old` and `/var/backups/dpkg.status.0` BOTH corrupt as well
- `apt update` fails with `E: Encountered a section with no Package: header`
- `apt install` cannot proceed
- `~/.ssh/authorized_keys` repeatedly disappears across reboots

### Root cause: Counterfeit SD card

`dmesg` shows EXT4 filesystem errors within the first 30 seconds of boot (before any user activity):
```
[27.053153] EXT4-fs error (device mmcblk0p2): bg 64: bad block bitmap checksum
[27.064497] EXT4-fs error (device mmcblk0p2): bg 79: bad block bitmap checksum
[27.620459] EXT4-fs error (device mmcblk0p2): bg 126: bad block bitmap checksum
[27.658684] EXT4-fs error (device mmcblk0p2): bg 243: bad block bitmap checksum
[27.709413] EXT4-fs error (device mmcblk0p2): bg 368: bad block bitmap checksum
[27.751896] EXT4-fs error (device mmcblk0p2): bg 496: bad block bitmap checksum
[27.785145] EXT4-fs error (device mmcblk0p2): bg 624: bad block bitmap checksum
[27.801010] EXT4-fs error (device mmcblk0p2): bg 752: bad block bitmap checksum
[27.818386] EXT4-fs error (device mmcblk0p2): bg 880: bad block bitmap checksum
[27.835817] EXT4-fs error (device mmcblk0p2): bg 1008: bad block bitmap checksum
```

Card identity (raw CID register from `/sys/block/mmcblk0/device/`):
```
name:    asdfg          ← keyboard placeholder, NOT a real product name
manfid:  0x000005       ← claims SanDisk
oemid:   0x000c         ← unregistered OEM ID
serial:  0x00000012     ← suspiciously low (real cards have larger serials)
date:    12/2025
size:    2097152000     ← reports 1TB (1,073,741,824,000 bytes)
```

**Conclusion:** The card is a counterfeit. The product name "asdfg" is a keyboard placeholder, the OEM ID is unregistered, and the serial is implausibly low. Counterfeit "1TB" cards are typically 16-32GB internally with firmware that lies about capacity. Writing beyond real capacity causes data wrap-around → corruption of the very blocks being modified (which is why fresh-write data — dpkg databases, freshly built binaries, authorized_keys — gets corrupted while OS image data stays intact).

### Why reflashing didn't help
The Imager wrote the OS image starting at sector 0. The image is small enough (~2-4GB) to fit in the card's real capacity, so it boots. But as soon as the OS starts writing new data (apt installs, log files, user files), those writes hit blocks beyond the real capacity and get silently dropped or wrapped around, corrupting other data.

### Decision
- This card is unusable and should be physically destroyed (don't accidentally re-use)
- An NVMe SSD via PCIe HAT is the correct path forward — it eliminates the SD reliability problem entirely and provides ~10x faster model loading (already in DESIGN-MAI-001 as a future expansion)
- Continue platform development under PLAN-MAI-003

### Lessons learned
1. **Always verify SD card identity** via `cat /sys/block/mmcblk0/device/name` after first boot. Reject any card with placeholder names ("asdfg", "test", numeric strings, etc.)
2. **Buy SD cards from authorized resellers only** — not Amazon Marketplace, AliExpress, eBay, etc. The 1TB price point is the most-counterfeited segment.
3. **Run `f3probe` from h2testw equivalent before trusting any new card** — actively writes-and-verifies the full claimed capacity to detect fake cards.
4. **Watch dmesg on first boot** for early EXT4 errors — they appear within seconds and are an unmistakable hardware-failure signal.
