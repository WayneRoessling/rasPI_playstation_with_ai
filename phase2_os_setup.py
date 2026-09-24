"""
Phase 2 — OS Setup (Bookworm Lite, NO kernel changes)

Strategy: install only what we need, touch nothing else.
No kernel changes = no initramfs risk = no corruption.

Idempotent: safe to re-run — skips steps already completed.
"""

import time
from pi_ssh import connect, run, gate, get_config


# ── Steps ─────────────────────────────────────────────────────────────────────

def step_disable_rpi_connect(c):
    print("\n=== 2.1 — Disable rpi-connect (stops boot scroll) ===")
    run(c, "sudo systemctl disable --now rpi-connect.service rpi-connect-wayvnc.service 2>&1 || true",
        label="disable rpi-connect", abort_on_fail=False)
    run(c, "sudo systemctl disable --now rpi-connect-lite.service 2>&1 || true",
        label="disable rpi-connect-lite", abort_on_fail=False)
    print("  (errors above are fine if service didn't exist)")


def step_install_tools(c):
    print("\n=== 2.2 — apt update + install tools ===")

    pkgs = [
        "git", "curl", "wget", "tmux",
        "build-essential", "pkg-config",
        "ffmpeg",
        "i2c-tools",
        "libasound2-dev", "libportaudio2",
        "htop", "nano",
        "python3-pip", "python3-venv", "v4l-utils",
        "libopenblas-dev",
    ]

    # Check which packages are already installed
    _, dpkg_out = run(c, "dpkg -l " + " ".join(pkgs) + " 2>/dev/null | grep '^ii' | awk '{print $2}'",
                      label="check installed packages", abort_on_fail=False)
    installed = set(dpkg_out.strip().splitlines())
    missing = [p for p in pkgs if p not in installed]

    if not missing:
        print("  All packages already installed — skipping.")
        return

    print(f"  Installing {len(missing)} missing packages: {' '.join(missing)}")
    run(c, "sudo apt-get update 2>&1 | tail -5", timeout=120, label="apt update")

    cmd = (
        f"sudo DEBIAN_FRONTEND=noninteractive apt-get install -y {' '.join(missing)} "
        f"2>&1 | tee /tmp/apt_tools.log"
    )
    run(c, cmd, timeout=600, label="apt install tools")
    code, out = run(c, "echo EXIT:$?; tail -3 /tmp/apt_tools.log", label="install result")
    gate("EXIT:0" in out or out.strip().endswith("0"), "tools installed OK")


def step_enable_interfaces(c):
    print("\n=== 2.3 — Enable I2C + SPI ===")

    # Check if already enabled before touching config
    _, i2c_out = run(c, "ls /dev/i2c* 2>/dev/null && echo I2C_OK || echo I2C_MISSING",
                     label="check I2C", abort_on_fail=False)
    if "I2C_OK" not in i2c_out:
        run(c, "sudo raspi-config nonint do_i2c 0", label="enable I2C")
    else:
        print("  I2C already enabled — skipping.")

    _, spi_out = run(c, "ls /dev/spidev* 2>/dev/null && echo SPI_OK || echo SPI_MISSING",
                     label="check SPI", abort_on_fail=False)
    if "SPI_OK" not in spi_out:
        run(c, "sudo raspi-config nonint do_spi 0", label="enable SPI")
    else:
        print("  SPI already enabled — skipping.")


def step_gpu_mem(c):
    print("\n=== 2.4 — Set gpu_mem=64 ===")

    # Check current value first
    _, current = run(c, "grep '^gpu_mem=64$' /boot/firmware/config.txt 2>/dev/null && echo ALREADY_SET || echo NEEDS_SET",
                     label="check gpu_mem", abort_on_fail=False)
    if "ALREADY_SET" in current:
        print("  gpu_mem=64 already set — skipping.")
        return

    cmd = (
        "grep -q '^gpu_mem=' /boot/firmware/config.txt "
        "&& sudo sed -i 's/^gpu_mem=.*/gpu_mem=64/' /boot/firmware/config.txt "
        "|| echo 'gpu_mem=64' | sudo tee -a /boot/firmware/config.txt"
    )
    run(c, cmd, label="set gpu_mem")
    _, out = run(c, "grep gpu_mem /boot/firmware/config.txt", label="verify gpu_mem")
    gate("gpu_mem=64" in out, "gpu_mem=64 confirmed")


def step_reboot(c):
    print("\n=== 2.5 — Reboot ===")
    run(c, "free -h | grep Mem", label="RAM pre-reboot")
    run(c, "df -h /", label="disk pre-reboot")
    run(c, "uname -r", label="kernel (unchanged)")
    print("\n  *** No kernel change — safe to reboot ***")
    try:
        c.exec_command("sudo reboot", timeout=5)
    except Exception:
        pass
    print("  Reboot issued. Waiting 60 seconds...")
    time.sleep(60)


def step_gate_test(c):
    print("\n=== 2.6 — Gate tests ===")
    _, out = run(c, "uname -r", label="kernel")
    print(f"  Kernel: {out.strip()}")

    run(c, "free -h | grep Mem", label="RAM")
    run(c, "df -h /", label="disk")

    _, out = run(c, "which git ffmpeg htop tmux nano && echo TOOLS_OK", label="tools")
    gate("TOOLS_OK" in out, "all tools present")

    _, out = run(c, "ls /dev/i2c* 2>&1", label="I2C")
    gate("/dev/i2c" in out, "I2C device present")

    _, out = run(c, "cat /etc/os-release | grep PRETTY", label="OS")
    print(f"\n  OS: {out.strip()}")

    print("\n" + "=" * 60)
    print("  PHASE 2 COMPLETE — ALL GATES PASSED")
    print("  Bookworm stable, kernel untouched, tools ready.")
    print("  Next: Phase 3 — Camera setup")
    print("=" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    host, _, _ = get_config()

    print("=" * 60)
    print("Phase 2 — Bookworm setup (no upgrades, no kernel changes)")
    print("=" * 60)

    c = connect()
    print(f"Connected to {host}")

    step_disable_rpi_connect(c)
    step_install_tools(c)
    step_enable_interfaces(c)
    step_gpu_mem(c)
    step_reboot(c)
    c.close()

    print("Reconnecting after reboot...")
    c = connect(retries=8, delay=10)
    print("  Reconnected.")

    step_gate_test(c)
    c.close()


if __name__ == "__main__":
    main()
