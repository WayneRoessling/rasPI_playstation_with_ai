# PLAN-MAI-003 — USB-NVMe Migration & Full Automated Setup

**Plan:** PLAN-MAI-003
**Project:** Mini-AI
**Status:** Active — Ready to execute (all hardware on hand)
**Created:** 2026-04-07
**Supersedes:** PLAN-MAI-002 (abandoned — counterfeit SD card)

---

## Background

PLAN-MAI-002 attempted a fresh reflash of the 1TB microSD card but failed identically to the previous attempt. Investigation found the SD card is **counterfeit hardware** (raw CID register reports product name `asdfg`, unregistered OEM ID, implausibly low serial). EXT4 filesystem errors appear within 30 seconds of boot, before any user activity, and dpkg databases corrupt within minutes of any write activity.

**Decision:** Eliminate SD storage entirely. Boot the Pi 5 directly from a 2TB NVMe SSD in a USB 3.0 enclosure. Pi 5 supports USB boot natively and USB 3.0 (5 Gbps) is more than fast enough for Mini-AI's workload.

---

## Hardware (all on hand)

| Item | Status | Notes |
|------|--------|-------|
| Raspberry Pi 5 16GB | Have | |
| **2TB NVMe SSD in USB enclosure** | Have | Will be the boot/root drive |
| SanDisk 64GB microSD | Have | One-time use for bootloader update only |
| USB-C 5V/5A power supply | Have | Critical — see "Power" section below |
| Logitech C920 USB camera | Have | |
| Yahboom YB-MAE02-V1.0 voice module | Have | |
| Ethernet + Wi-Fi network | Have | |

**Counterfeit 1TB microSD: discard.** Do not reuse.

---

## Why USB-NVMe (no PCIe HAT)

| | USB 3.0 NVMe | PCIe HAT NVMe | microSD (SD card) |
|---|---|---|---|
| Sequential read | ~400 MB/s (USB 3.0 ceiling) | ~800 MB/s | ~50-100 MB/s |
| Random IOPS | ~50k+ | ~80k+ | ~2k |
| LLaVA 7B cold load | ~3-4s | ~1-2s | ~10s |
| Reliability | Excellent | Excellent | Variable, counterfeit-prone |
| Setup complexity | Plug and play | Physical install + cable | Simple |
| Cost | $0 (have it) | ~$25 HAT | ~$25 (genuine) |

USB 3.0 is ~2x slower than PCIe but **4-8x faster than SD** and — more importantly — it's a real storage device that won't corrupt itself. For Mini-AI's workload (model loaded once, kept resident in RAM via Ollama `keep_alive`), the cold-load difference between USB-NVMe and PCIe-NVMe is irrelevant.

---

## Power Requirements

USB-NVMe enclosures can pull **0.5-1A under sustained load**. Combined with the Pi 5 itself (~1.5A under LLM load), the camera, and the audio module, total draw can hit ~3A.

**Required:** Official Raspberry Pi 27W USB-C power supply (5.1V / 5A), or equivalent. The older 2.5A "Pi 4 era" supplies will cause undervoltage and silent SSD I/O failures during model downloads.

**Verify after first boot:**
```bash
vcgencmd get_throttled
# Expected: throttled=0x0
# Anything non-zero (especially bits 0/16) = undervoltage = swap power supply
```

---

## Migration Procedure

### Phase A — Bootloader Update (one-time, on the 64GB SanDisk)

The Pi 5's bootloader needs to support USB boot priority. Recent Pi 5s ship with this enabled, but verify.

1. Flash the **64GB SanDisk** with Raspberry Pi OS using Raspberry Pi Imager (default OS choice — just need a working boot environment for the bootloader update).
2. Boot the Pi from the 64GB SD card.
3. SSH in and update the bootloader:
   ```bash
   sudo rpi-eeprom-update -a
   sudo reboot
   ```
4. After reboot, set boot order to USB-first:
   ```bash
   sudo raspi-config
   # Advanced Options → Boot Order → USB Boot
   # Or via EEPROM editor:
   sudo rpi-eeprom-config --edit
   # Set: BOOT_ORDER=0xf41   (USB → SD → repeat)
   ```
5. Verify:
   ```bash
   vcgencmd bootloader_config | grep BOOT_ORDER
   # Expected: BOOT_ORDER=0xf41 (or similar with 4 first)
   ```
6. Power off the Pi.

### Phase B — Image the NVMe via the USB Enclosure

Do this on your **Windows workstation**, not on the Pi.

1. Plug the USB-NVMe enclosure into your Windows PC.
2. Launch Raspberry Pi Imager:
   - **Device:** Raspberry Pi 5
   - **OS:** Use the **same default Raspberry Pi OS** that Imager wrote to the 64GB SanDisk in Phase A — that build is known to work on this Pi. (Bookworm Lite was tried in PLAN-MAI-002 and gave us trouble; do not switch OS variants now.)
   - **Storage:** the NVMe (will appear as a USB drive)
3. Click the gear icon for OS customisation:
   - Hostname: `mini-ai-01`
   - Username: `<your-username>`
   - Password: Pi admin password from your password manager (setup scripts read it from `.env` via `MINI_AI_PASS`)
   - Wi-Fi: configured (SSID + password + country US)
   - SSH: **enabled with public-key authentication**
   - Public key: paste contents of `~/.ssh/id_ed25519_mini_ai.pub`
4. Write + verify (~5-10 min on USB 3.0)
5. Eject safely.

> **Why preconfigure the SSH key in Imager?** PLAN-MAI-002 found that cloud-init / first-boot can wipe `~/.ssh/authorized_keys` when keys are pushed post-boot. Baking the key into the image avoids this entirely.

### Phase C — Boot the Pi from USB-NVMe

1. Power off the Pi.
2. **Remove the SanDisk SD card** (eject it physically).
3. Plug the USB-NVMe enclosure into a **blue USB 3.0 port** (not the black USB 2.0 ports).
4. Power on.
5. Wait ~90 seconds for first boot to complete.

### Phase D — First Boot Verification

From your workstation:

```bash
cd rasPI_playstation_with_ai   # your clone of this repo

# Connect via SSH key (preconfigured in image)
ssh -i ~/.ssh/id_ed25519_mini_ai <user>@<pi-ip>

# Verify root is on the USB device, not SD
mount | grep " / "
# Expected: /dev/sda2 on / type ext4 ...
#   (USB devices appear as sda/sdb, not nvme0n1, when going through USB bridge)

# Verify NO filesystem errors
sudo dmesg | grep -iE "ext4 error|i/o error|usb.*error"
# Expected: empty

# Verify dpkg integrity
file /var/lib/dpkg/status
# Expected: ASCII text, with very long lines

# Verify no power issues
vcgencmd get_throttled
# Expected: throttled=0x0

# Verify OS edition matches the SanDisk install
cat /etc/os-release | grep PRETTY
# Expected: PRETTY_NAME="Raspberry Pi OS ..." (same edition as on the 64GB SanDisk)

# Capacity check
df -h /
# Expected: ~1.8TB available on a 2TB drive
```

**If ANY of the above fail, stop and diagnose. Do NOT continue.**

### Phase E — Run the Existing Setup Pipeline

The `setup_all.py` script and `pi_ssh.py` helpers are storage-agnostic.

```bash
cd rasPI_playstation_with_ai   # your clone of this repo

# .env should already point at <pi-ip> with SSH key path

# Run all setup phases (2-8). Phase 8 uploads the app code
# (voice_pipeline.py, mini_ai_config.py, mini_ai_panel.py, overlay/, desktop/,
# test_e2e_pipeline.py) to ~/mini-ai and installs its Python deps.
python setup_all.py

# Health check
python test_pi_state.py
# Expected: 13/13 checks pass

# Run E2E test
ssh mini-ai '~/mini-ai/.venv/bin/python ~/mini-ai/test_e2e_pipeline.py'
# Expected: All 5 stages pass
```

After changing app code on the workstation, redeploy with `python setup_all.py --only 8`.

Phase 4 pulls every model any preset can switch to (`mini_ai_config.PRESETS`) plus
the overlay model (`MINI_AI_OVERLAY_MODEL`, default `qwen2.5:14b`, ~9GB); phase 6
downloads every Piper voice in `mini_ai_config.VOICES`.

---

## Pre-Flight Code Fixes (already applied 2026-04-07)

These were made during the PLAN-MAI-002 attempt and remain valid:

| File | Fix | Reason |
|------|-----|--------|
| `test_pi_state.py` | OpenCV check uses `~/mini-ai/.venv/bin/python` | OpenCV is pip-installed in venv, not system |
| `setup_all.py` | Removed `voice_pipeline.py` gate from phase 6 | File is SCP'd AFTER setup_all.py, not before |
| `setup_all.py` | Added `_repush_key()` after phase 2 reboot | Cloud-init / first-boot can wipe `~/.ssh` |
| `setup_all.py` phase 2 | No `python3-opencv` apt package, no OpenCV gate | Causes segfaults; pip opencv-python-headless is installed in phase 3 (the standalone `phase2_os_setup.py` has since been removed) |

---

## Open Issues to Watch (carried over from PLAN-MAI-002)

1. **Cloud-init wipes `~/.ssh/authorized_keys`** — observed in PLAN-MAI-002. Mitigation: Imager preconfigures the key directly into the image (Phase B step 3) so it's baked in before first boot rather than pushed afterward.
2. **gpu_mem=64 may not persist** — needs verification post-reboot. Goes into `/boot/firmware/config.txt` which is on the FAT32 boot partition.
3. **Phase 2 reboot reconnect timing** — `setup_all.py` waits 60s after `sudo reboot`. NVMe boots faster than SD, so this should be fine. If reconnect fails, increase to 90s.
4. **Apt-list / dpkg corruption** — was a symptom of the bad SD card. Should NOT recur on USB-NVMe. **If it does, stop immediately** — it indicates either a bad NVMe, a bad USB enclosure bridge chip, or undervoltage. Check `vcgencmd get_throttled` and `dmesg` first.

---

## Estimated Total Time

| Phase | Duration |
|-------|----------|
| Phase A: Flash SanDisk + bootloader update | 20 min |
| Phase B: Image NVMe via USB enclosure | 10 min |
| Phase C: Boot Pi from USB-NVMe | 5 min |
| Phase D: First boot verification | 5 min |
| Phase E: `setup_all.py` (Phases 2-8, incl. ~20GB of models) | 45-90 min |
| E2E test | 5 min |
| **Total** | **~75-105 min** |

---

## Completion Criteria

- [ ] 64GB SanDisk boots cleanly (Pi hardware verified)
- [ ] Bootloader updated, USB boot priority set
- [ ] NVMe imaged with the same OS edition that worked on the SanDisk + preconfigured SSH key
- [ ] Pi boots from USB-NVMe with `/` mounted on `/dev/sda2`
- [ ] `dmesg` shows zero filesystem errors after first boot
- [ ] `vcgencmd get_throttled` returns `0x0` (no undervoltage)
- [ ] `file /var/lib/dpkg/status` returns `ASCII text` (not `data`)
- [ ] OS edition matches the working SanDisk install
- [ ] `setup_all.py` completes all phases 2-8 without intervention
- [ ] `test_pi_state.py` — 13/13 checks pass
- [ ] `test_e2e_pipeline.py` — all 5 stages pass
- [ ] Live voice pipeline test: speak → hear response

---

## Out-of-scope (deferred to future plans)

- Wake word detection (PLAN-MAI-004 candidate)
- Multi-turn conversation memory
- Web UI / Home Assistant integration
- Dual-camera setup
- Larger LLMs (Mistral 13B, etc.) — possible with NVMe's faster model loading
- PCIe HAT upgrade (only worth it if cold-load latency becomes a real bottleneck)
