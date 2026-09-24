"""
Health check / gate test for Mini-AI Pi.

Connects to the Pi and asserts all expected conditions. Can be used as:
  - Post-setup validation (after any phase)
  - Regression check before starting a new phase
  - Automated health probe

Exit codes:
  0 = all checks passed
  1 = one or more checks failed (summary printed)
"""

import sys
from pi_ssh import connect, run

CHECKS = []
FAILURES = []


def check(name, cmd, expect_in_output):
    """Run a command and assert the output contains expected string."""
    CHECKS.append(name)
    _, out = run(client, cmd, label=name, abort_on_fail=False)
    if expect_in_output in out:
        print(f"  PASS: {name}")
    else:
        FAILURES.append(name)
        print(f"  FAIL: {name} — expected '{expect_in_output}' in output")


# ── Connect ───────────────────────────────────────────────────────────────────

print("=" * 60)
print("Mini-AI Pi Health Check")
print("=" * 60)

client = connect()

# ── Phase 1 checks (basic boot) ──────────────────────────────────────────────

check("kernel running",
      "uname -r",
      "6.")

check("disk expanded (>100G)",
      "df -h / | awk 'NR==2 {s=$2; sub(/[GT]/,\"\",s); if ((s+0) >= 100 || $2 ~ /T/) print \"DISK_OK\"; else print \"DISK_TOO_SMALL\"}'",
      "DISK_OK")

check("SSH key auth",
      "echo SSH_OK",
      "SSH_OK")

# ── Phase 2 checks (OS setup) ────────────────────────────────────────────────

check("core tools installed",
      "which git curl ffmpeg htop tmux nano && echo TOOLS_OK",
      "TOOLS_OK")

check("build tools installed",
      "which gcc make pkg-config && echo BUILD_OK",
      "BUILD_OK")

check("I2C device present",
      "ls /dev/i2c* 2>/dev/null && echo I2C_OK || echo I2C_MISSING",
      "I2C_OK")

check("SPI device present",
      "ls /dev/spidev* 2>/dev/null && echo SPI_OK || echo SPI_MISSING",
      "SPI_OK")

check("gpu_mem=64",
      "grep '^gpu_mem=64' /boot/firmware/config.txt && echo GPU_OK || echo GPU_MISSING",
      "GPU_OK")

check("OpenCV importable",
      '~/mini-ai/.venv/bin/python -c "import cv2; print(\'CV2_OK\')" 2>&1',
      "CV2_OK")

# ── Phase 3 checks (camera) ──────────────────────────────────────────────────

check("USB camera detected",
      "v4l2-ctl --list-devices 2>/dev/null | grep -i -A1 'logitech\\|webcam\\|video' && echo CAM_OK || echo CAM_MISSING",
      "CAM_OK")

# ── Phase 4 checks (LLM) ─────────────────────────────────────────────────────

check("Ollama service",
      "curl -s http://localhost:11434/api/tags 2>/dev/null && echo OLLAMA_OK || echo OLLAMA_MISSING",
      "OLLAMA_OK")

# ── Phase 5 checks (audio) ───────────────────────────────────────────────────

check("ALSA playback device",
      "aplay -l 2>/dev/null | grep -i card && echo APLAY_OK || echo APLAY_MISSING",
      "APLAY_OK")

check("ALSA capture device",
      "arecord -l 2>/dev/null | grep -i card && echo AREC_OK || echo AREC_MISSING",
      "AREC_OK")

# ── Summary ───────────────────────────────────────────────────────────────────

client.close()

print("\n" + "=" * 60)
print(f"  {len(CHECKS)} checks run, {len(CHECKS) - len(FAILURES)} passed, {len(FAILURES)} failed")

if FAILURES:
    print("\n  FAILED:")
    for f in FAILURES:
        print(f"    - {f}")
    print("\n  (Failures in later phases are expected if that phase hasn't run yet.)")
    print("=" * 60)
    sys.exit(1)
else:
    print("\n  ALL CHECKS PASSED")
    print("=" * 60)
    sys.exit(0)
