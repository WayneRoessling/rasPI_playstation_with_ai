#!/usr/bin/env python3
"""
Mini-AI Full Setup — Phases 2-8

Runs all setup phases on a freshly flashed Pi in one shot.
Prerequisites:
  1. Pi imaged with Raspberry Pi OS 64-bit (Imager preconfigures hostname,
     Wi-Fi and the SSH public key — see PLAN-MAI-003 Phase B) and booted
  2. .env configured with PI host/user/key

Usage:
  python setup_all.py              # run all phases
  python setup_all.py --from 4     # resume from phase 4
  python setup_all.py --only 8     # run only phase 8 (redeploy app code)
"""

import argparse
import sys
import time
import os

from pi_ssh import connect, run as _run, gate, get_config, get_password, connect_password
from mini_ai_config import PRESETS, VOICES, load_preset

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# Ollama model for the overlay tool-use loop (see voice_pipeline.OVERLAY_MODEL).
OVERLAY_MODEL = os.environ.get("MINI_AI_OVERLAY_MODEL", "qwen2.5:14b")


def run(c, cmd, **kwargs):
    """pi_ssh.run with pipefail on, so a failing `cmd | tail -N` aborts the phase."""
    return _run(c, cmd, pipefail=True, **kwargs)


def _repush_key():
    """Re-push SSH key via password auth (first reboot can wipe authorized_keys)."""
    host, user, key_path = get_config()
    pubkey_path = key_path + ".pub"
    if not os.path.exists(pubkey_path):
        print(f"  WARNING: Public key not found at {pubkey_path}, skipping re-push")
        return
    with open(pubkey_path) as f:
        pubkey = f.read().strip()
    try:
        password = get_password()
        c, t = connect_password(host, user, password)
        cmds = [
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh",
            f'grep -qxF "{pubkey}" ~/.ssh/authorized_keys 2>/dev/null || echo "{pubkey}" >> ~/.ssh/authorized_keys',
            "chmod 600 ~/.ssh/authorized_keys",
        ]
        for cmd in cmds:
            _, stdout, _ = c.exec_command(cmd)
            # Block until the command finishes — closing the transport early can
            # cut off the authorized_keys write.
            code = stdout.channel.recv_exit_status()
            if code != 0:
                raise RuntimeError(f"`{cmd.split()[0]}` exited {code}")
        t.close()
        print("  SSH key re-pushed OK")
    except Exception as e:
        print(f"  Key re-push skipped ({e}) — key auth may already work")


# ── Phase 2: OS Setup ────────────────────────────────────────────────────────

def phase2(c):
    print("\n" + "=" * 60)
    print("  PHASE 2 — OS Setup")
    print("=" * 60)

    # 2.1 Disable rpi-connect
    run(c, "sudo systemctl disable --now rpi-connect.service rpi-connect-wayvnc.service 2>&1 || true",
        label="disable rpi-connect", abort_on_fail=False)
    run(c, "sudo systemctl disable --now rpi-connect-lite.service 2>&1 || true",
        label="disable rpi-connect-lite", abort_on_fail=False)

    # 2.2 Install tools
    pkgs = [
        "git", "curl", "wget", "tmux", "cmake",
        "build-essential", "pkg-config",
        "ffmpeg",
        "i2c-tools",
        "libasound2-dev", "libportaudio2",
        "htop", "nano",
        "python3-pip", "python3-venv",
        "v4l-utils",
        "libopenblas-dev", "zstd",
    ]
    _, dpkg_out = run(c, "dpkg -l " + " ".join(pkgs) + " 2>/dev/null | grep '^ii' | awk '{print $2}'",
                      label="check installed", abort_on_fail=False)
    installed = set(dpkg_out.strip().splitlines())
    missing = [p for p in pkgs if p not in installed]

    if missing:
        print(f"  Installing {len(missing)} packages: {' '.join(missing)}")
        run(c, "sudo apt-get update 2>&1 | tail -5", timeout=120, label="apt update")
        run(c, f"sudo DEBIAN_FRONTEND=noninteractive apt-get install -y {' '.join(missing)} 2>&1 | tail -10",
            timeout=600, label="apt install")
    else:
        print("  All packages already installed.")

    # 2.3 Enable I2C + SPI
    _, i2c = run(c, "ls /dev/i2c* 2>/dev/null && echo OK || echo MISSING", label="check I2C", abort_on_fail=False)
    if "OK" not in i2c:
        run(c, "sudo raspi-config nonint do_i2c 0", label="enable I2C")
    _, spi = run(c, "ls /dev/spidev* 2>/dev/null && echo OK || echo MISSING", label="check SPI", abort_on_fail=False)
    if "OK" not in spi:
        run(c, "sudo raspi-config nonint do_spi 0", label="enable SPI")

    # 2.4 GPU memory
    _, gpu = run(c, "grep '^gpu_mem=64$' /boot/firmware/config.txt && echo GPU_SET || echo GPU_UNSET",
                 label="check gpu_mem", abort_on_fail=False)
    if "GPU_SET" not in gpu:
        run(c, "grep -q '^gpu_mem=' /boot/firmware/config.txt "
            "&& sudo sed -i 's/^gpu_mem=.*/gpu_mem=64/' /boot/firmware/config.txt "
            "|| echo 'gpu_mem=64' | sudo tee -a /boot/firmware/config.txt",
            label="set gpu_mem=64")

    # 2.5 Reboot
    run(c, "uname -r", label="kernel (pre-reboot)")
    print("\n  Rebooting...")
    try:
        c.exec_command("sudo reboot", timeout=5)
    except Exception:
        pass
    time.sleep(60)

    # Re-push SSH key (first reboot on fresh Bookworm can wipe authorized_keys)
    print("  Re-pushing SSH key after reboot...")
    _repush_key()

    # Reconnect
    print("  Reconnecting...")
    c2 = connect(retries=10, delay=10)

    # Gate tests
    _, out = run(c2, "which git ffmpeg htop tmux nano cmake && echo TOOLS_OK", label="tools")
    gate("TOOLS_OK" in out, "all tools present")
    _, out = run(c2, "ls /dev/i2c* 2>&1", label="I2C")
    gate("/dev/i2c" in out, "I2C present")

    print("\n  PHASE 2 COMPLETE")
    return c2


# ── Phase 3: Camera ──────────────────────────────────────────────────────────

def phase3(c):
    print("\n" + "=" * 60)
    print("  PHASE 3 — USB Camera Setup")
    print("=" * 60)

    _, out = run(c, "v4l2-ctl --list-devices 2>&1", label="list cameras", abort_on_fail=False)
    gate("/dev/video" in out, "camera device detected")

    # Create venv and install OpenCV
    run(c, "mkdir -p ~/mini-ai", label="create project dir")
    _, venv = run(c, "test -d ~/mini-ai/.venv && echo EXISTS || echo MISSING",
                  label="check venv", abort_on_fail=False)
    if "MISSING" in venv:
        run(c, "python3 -m venv ~/mini-ai/.venv", label="create venv")

    _, cv2 = run(c, '~/mini-ai/.venv/bin/python -c "import cv2; print(cv2.__version__)" 2>&1',
                 label="check opencv", abort_on_fail=False)
    if "Error" in cv2 or cv2.strip() == "":
        run(c, "~/mini-ai/.venv/bin/pip install --no-cache-dir opencv-python-headless 2>&1 | tail -5",
            timeout=300, label="install opencv")

    # Test capture
    run(c, "mkdir -p ~/tests/camera")
    run(c, '~/mini-ai/.venv/bin/python -c "'
        'import cv2, os; cap=cv2.VideoCapture(0); '
        'cap.set(3,1920); cap.set(4,1080); '
        'r,f=cap.read(); cap.release(); '
        'cv2.imwrite(os.path.expanduser(\\\"~/tests/camera/test_still.jpg\\\"),f); '
        'print(f\\\"Captured: {f.shape}\\\")'
        '" 2>&1', label="capture test image")

    _, out = run(c, "ls -lh ~/tests/camera/test_still.jpg", label="verify image")
    gate("test_still.jpg" in out, "image captured")

    print("\n  PHASE 3 COMPLETE")
    return c


# ── Phase 4: LLM ─────────────────────────────────────────────────────────────

def phase4(c):
    print("\n" + "=" * 60)
    print("  PHASE 4 — Ollama + Models")
    print("=" * 60)

    # Check if already installed
    _, ollama = run(c, "which ollama 2>&1 || echo MISSING", label="check ollama", abort_on_fail=False)

    if "MISSING" in ollama:
        # Need wlan0 for ollama.com
        ensure_wlan0_default(c)

        # Download and patch installer
        run(c, "curl -fsSL --interface wlan0 --connect-timeout 15 https://ollama.com/install.sh -o /tmp/ollama_install.sh",
            timeout=30, label="download installer")

        # Create curl wrapper for wlan0
        run(c, "mkdir -p /tmp/ollama_bin && "
            "echo '#!/bin/bash' > /tmp/ollama_bin/curl && "
            "echo 'exec /usr/bin/curl --interface wlan0 \"$@\"' >> /tmp/ollama_bin/curl && "
            "chmod +x /tmp/ollama_bin/curl",
            label="create curl wrapper")

        run(c, 'sudo bash -c \'export PATH="/tmp/ollama_bin:$PATH" && bash /tmp/ollama_install.sh\' 2>&1 | tail -10',
            timeout=600, label="install ollama")

        run(c, "rm -rf /tmp/ollama_bin", label="cleanup wrapper")
        restore_eth0_default(c)

    _, out = run(c, "ollama --version 2>&1", label="ollama version")
    gate("ollama" in out.lower(), "ollama installed")

    # Configure service
    run(c, "sudo systemctl enable ollama 2>&1 || true", label="enable ollama", abort_on_fail=False)
    run(c, "sudo systemctl start ollama 2>&1 || true", label="start ollama", abort_on_fail=False)
    time.sleep(3)

    _, out = run(c, "curl -s http://localhost:11434/api/tags", label="check ollama API", abort_on_fail=False)

    # Pull models (need wlan0 route)
    models = _ollama_models()
    _, listing = run(c, "ollama list 2>&1", label="list models", abort_on_fail=False)

    for model in models:
        if _has_model(listing, model):
            continue
        ensure_wlan0_default(c)
        run(c, f"ollama pull {model} 2>&1 | tail -5", timeout=3600, label=f"pull {model}")
        restore_eth0_default(c)

    # Verify
    _, listing = run(c, "ollama list 2>&1", label="verify models")
    for model in models:
        gate(_has_model(listing, model), f"{model} present")

    # Quick text test against the active preset's text model
    text_model = load_preset().text_model
    _, out = run(c, "curl -s http://localhost:11434/api/generate "
                 f"""-d '{{"model":"{text_model}","prompt":"2+2=","stream":false}}' 2>&1""",
                 timeout=120, label="text inference test")
    gate('"response"' in out, "text inference works")

    print("\n  PHASE 4 COMPLETE")
    return c


def _ollama_models():
    """Active preset first, then every model the picker can switch to, then the overlay model."""
    active = load_preset()
    candidates = [active.text_model, active.vision_model]
    for p in PRESETS:
        candidates += [p.text_model, p.vision_model]
    candidates.append(OVERLAY_MODEL)
    return list(dict.fromkeys(candidates))


def _has_model(listing, model):
    """True if `ollama list` output contains model (bare names match `:latest`)."""
    names = {line.split()[0] for line in listing.splitlines()[1:] if line.strip()}
    return model in names or f"{model}:latest" in names


# ── Phase 5: Audio ────────────────────────────────────────────────────────────

def phase5(c):
    print("\n" + "=" * 60)
    print("  PHASE 5 — Audio Devices")
    print("=" * 60)

    _, out = run(c, "aplay -l 2>&1", label="playback devices", abort_on_fail=False)
    gate("card" in out.lower(), "playback device found")

    _, out = run(c, "arecord -l 2>&1", label="capture devices", abort_on_fail=False)
    gate("card" in out.lower(), "capture device found")

    print("\n  PHASE 5 COMPLETE")
    return c


# ── Phase 6: Pipeline ────────────────────────────────────────────────────────

def phase6(c):
    print("\n" + "=" * 60)
    print("  PHASE 6 — Speech Pipeline")
    print("=" * 60)

    # 6.1 Whisper.cpp
    _, whisper = run(c, "test -f ~/whisper.cpp/build/bin/whisper-cli && echo EXISTS || echo MISSING",
                     label="check whisper", abort_on_fail=False)
    if "MISSING" in whisper:
        ensure_wlan0_default(c)
        run(c, "test -d ~/whisper.cpp || git clone https://github.com/ggerganov/whisper.cpp.git ~/whisper.cpp 2>&1 | tail -3",
            timeout=120, label="clone whisper.cpp")
        restore_eth0_default(c)

        run(c, "cd ~/whisper.cpp && cmake -B build 2>&1 | tail -5", timeout=60, label="cmake whisper")
        run(c, "cd ~/whisper.cpp && cmake --build build -j4 2>&1 | tail -5", timeout=300, label="build whisper")

    _, out = run(c, "file ~/whisper.cpp/build/bin/whisper-cli", label="verify whisper binary")
    gate("ELF" in out, "whisper-cli is valid ELF binary")

    # Download model
    _, model = run(c, "test -f ~/whisper.cpp/models/ggml-base.en.bin && echo EXISTS || echo MISSING",
                   label="check whisper model", abort_on_fail=False)
    if "MISSING" in model:
        ensure_wlan0_default(c)
        run(c, "cd ~/whisper.cpp && bash ./models/download-ggml-model.sh base.en 2>&1 | tail -5",
            timeout=120, label="download whisper model")
        restore_eth0_default(c)

    # 6.2 Piper TTS
    _, piper = run(c, "~/mini-ai/.venv/bin/piper --help 2>&1 | head -1",
                   label="check piper", abort_on_fail=False)
    if "usage" not in piper.lower():
        ensure_wlan0_default(c)
        run(c, "~/mini-ai/.venv/bin/pip install --no-cache-dir piper-tts 2>&1 | tail -5",
            timeout=300, label="install piper")
        restore_eth0_default(c)

    # Download every voice the picker offers (mini_ai_config.VOICES)
    run(c, "mkdir -p ~/piper-voices")
    for v in VOICES:
        _, voice = run(c, f"test -f ~/piper-voices/{v.file}.onnx.json && echo EXISTS || echo MISSING",
                       label=f"check piper voice {v.key}", abort_on_fail=False)
        if "MISSING" not in voice:
            continue
        ensure_wlan0_default(c)
        # Download to .part and rename so an interrupted run never leaves a truncated model.
        for ext, timeout in ((".onnx", 300), (".onnx.json", 60)):
            dest = f"~/piper-voices/{v.file}{ext}"
            run(c, f"curl -fSL -o {dest}.part {_piper_voice_url(v.file)}{ext} 2>&1 | tail -3 "
                f"&& mv {dest}.part {dest}",
                timeout=timeout, label=f"download {v.file}{ext}")
        restore_eth0_default(c)

    # 6.3 Install ollama python package
    _, ollama_py = run(c, '~/mini-ai/.venv/bin/python -c "import ollama; print(ollama.__version__)" 2>&1',
                       label="check ollama pkg", abort_on_fail=False)
    if "Error" in ollama_py:
        ensure_wlan0_default(c)
        run(c, "~/mini-ai/.venv/bin/pip install --no-cache-dir ollama 2>&1 | tail -5",
            timeout=120, label="install ollama pkg")
        restore_eth0_default(c)

    # 6.4 Round-trip test: TTS -> STT
    run(c, 'echo "Hello this is a test" | ~/mini-ai/.venv/bin/piper '
        '--model ~/piper-voices/en_US-lessac-medium.onnx '
        '--output_file /tmp/setup_tts_test.wav 2>&1',
        label="TTS test")
    run(c, "ffmpeg -y -i /tmp/setup_tts_test.wav -ar 16000 -ac 1 -c:a pcm_s16le /tmp/setup_stt_test.wav 2>&1 | tail -2",
        label="convert to 16kHz")
    _, out = run(c, "~/whisper.cpp/build/bin/whisper-cli -m ~/whisper.cpp/models/ggml-base.en.bin "
                "-f /tmp/setup_stt_test.wav --no-timestamps 2>&1 | grep -v whisper_",
                timeout=30, label="STT test")
    gate("hello" in out.lower() or "test" in out.lower(), "TTS->STT round-trip works")

    print("\n  PHASE 6 COMPLETE")
    return c


def _piper_voice_url(file):
    """HF URL (sans extension) for a Piper voice, e.g. en_GB-jenny_dioco-medium ->
    .../en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium"""
    locale, name, quality = file.split("-")
    lang = locale.split("_")[0]
    return (f"https://huggingface.co/rhasspy/piper-voices/resolve/main/"
            f"{lang}/{locale}/{name}/{quality}/{file}")


# ── Phase 7: VSCode Dev ──────────────────────────────────────────────────────

def phase7(c):
    print("\n" + "=" * 60)
    print("  PHASE 7 — VSCode Dev Environment")
    print("=" * 60)

    # Create .vscode settings
    run(c, "mkdir -p ~/mini-ai/.vscode")
    run(c, """cat > ~/mini-ai/.vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "$HOME/mini-ai/.venv/bin/python",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    },
    "files.watcherExclude": {
        "**/__pycache__/**": true,
        "**/.venv/**": true
    }
}
EOF""", label="write vscode settings")

    # Create requirements.txt on Pi
    run(c, """cat > ~/mini-ai/requirements.txt << 'EOF'
opencv-python-headless
piper-tts
ollama
EOF""", label="write requirements.txt")

    _, out = run(c, "cat ~/mini-ai/.vscode/settings.json", label="verify settings")
    gate("defaultInterpreterPath" in out, "vscode settings created")

    print("\n  PHASE 7 COMPLETE")
    print("\n  Next: Open VSCode, install Remote-SSH extension,")
    print("  connect to mini-ai, open ~/mini-ai folder.")
    return c


# ── Phase 8: Deploy app ──────────────────────────────────────────────────────

# Everything voice_pipeline.py / mini_ai_panel.py import at runtime, plus the
# desktop launchers. Paths are relative to the repo root and to ~/mini-ai.
DEPLOY_FILES = ["voice_pipeline.py", "mini_ai_config.py", "mini_ai_panel.py", "test_e2e_pipeline.py"]
DEPLOY_DIRS = ["overlay", "desktop"]
DEPLOY_SKIP_DIRS = {"__pycache__", "dev_assets", "node_modules"}
DEPLOY_REQUIREMENTS = ["overlay/scenario/requirements.txt", "overlay/pi5_hal/requirements.txt"]


def _deploy_paths():
    paths = list(DEPLOY_FILES)
    for top in DEPLOY_DIRS:
        for root, dirs, files in os.walk(os.path.join(REPO_DIR, top)):
            dirs[:] = [d for d in dirs if d not in DEPLOY_SKIP_DIRS and not d.startswith(".")]
            rel_root = os.path.relpath(root, REPO_DIR).replace(os.sep, "/")
            paths += [f"{rel_root}/{f}" for f in files if not f.endswith(".pyc")]
    return paths


def phase8(c):
    print("\n" + "=" * 60)
    print("  PHASE 8 — Deploy app code")
    print("=" * 60)

    _, home = run(c, "echo $HOME", label="remote home")
    dest = home.strip() + "/mini-ai"
    paths = _deploy_paths()

    remote_dirs = sorted({f"{dest}/{os.path.dirname(rel)}".rstrip("/") for rel in paths})
    run(c, "mkdir -p " + " ".join(f"'{d}'" for d in remote_dirs), label="create app dirs")

    sftp = c.open_sftp()
    for rel in paths:
        with open(os.path.join(REPO_DIR, rel), "rb") as f:
            data = f.read()
        if b"\0" not in data:
            # A Windows checkout (core.autocrlf) may be CRLF; `#!/bin/bash\r` won't run.
            data = data.replace(b"\r\n", b"\n")
        with sftp.open(f"{dest}/{rel}", "wb") as remote:
            remote.write(data)
    sftp.close()
    print(f"  Uploaded {len(paths)} files to {dest}")

    run(c, "chmod +x ~/mini-ai/voice_pipeline.py ~/mini-ai/mini_ai_panel.py ~/mini-ai/desktop/*.py "
        "~/mini-ai/desktop/*.sh", label="mark scripts executable")

    # The repo copies are user-agnostic: point shebangs at the venv and fill the
    # @HOME@ placeholder in the desktop launchers with this Pi's home directory.
    run(c, 'cd ~/mini-ai && sed -i "1s|^#!/usr/bin/env python3\\$|#!$HOME/mini-ai/.venv/bin/python3|" '
        "voice_pipeline.py mini_ai_panel.py desktop/*.py", label="point shebangs at venv")
    run(c, 'mkdir -p ~/Desktop && for f in ~/mini-ai/desktop/*.desktop; do '
        'dest="$HOME/Desktop/$(basename "$f")"; sed "s|@HOME@|$HOME|g" "$f" > "$dest" && chmod +x "$dest"; done',
        label="install desktop launchers")

    ensure_wlan0_default(c)
    reqs = " ".join(f"-r ~/mini-ai/{r}" for r in DEPLOY_REQUIREMENTS)
    run(c, f"~/mini-ai/.venv/bin/pip install --no-cache-dir {reqs} 2>&1 | tail -5",
        timeout=300, label="install overlay deps")
    restore_eth0_default(c)

    # Gate: every runtime import resolves inside the venv
    _, out = run(c, "cd ~/mini-ai && .venv/bin/python -c "
                 "'import mini_ai_config, yaml, requests, websocket; "
                 "from overlay.scenario.demo import SCENARIOS; print(\"IMPORTS_OK\", len(SCENARIOS))'",
                 label="verify imports")
    gate("IMPORTS_OK" in out, "app imports resolve on the Pi")

    print("\n  PHASE 8 COMPLETE")
    return c


# ── Network helpers ───────────────────────────────────────────────────────────

# The eth0 default route (as printed by `ip route show default dev eth0`) that
# ensure_wlan0_default() removed and restore_eth0_default() must put back.
_removed_eth0_route = None


def ensure_wlan0_default(c):
    """Drop the eth0 default route (if any) so external downloads go via wlan0.

    The route is read from the Pi rather than hardcoded, so this works on any
    LAN / DHCP gateway. No eth0 default route -> nothing to do.
    """
    global _removed_eth0_route
    if _removed_eth0_route:
        return
    _, out = run(c, "ip route show default dev eth0", label="eth0 default route", abort_on_fail=False)
    route = out.strip().splitlines()[0] if out.strip() else ""
    if not route:
        return
    run(c, f"sudo ip route del {route} dev eth0", label="route -> wlan0")
    _removed_eth0_route = route


def restore_eth0_default(c):
    """Put back the eth0 default route removed by ensure_wlan0_default()."""
    global _removed_eth0_route
    if not _removed_eth0_route:
        return
    run(c, f"sudo ip route replace {_removed_eth0_route} dev eth0", label="route -> eth0")
    _removed_eth0_route = None


# ── Main ──────────────────────────────────────────────────────────────────────

PHASES = {
    2: ("OS Setup", phase2),
    3: ("USB Camera", phase3),
    4: ("Ollama + Models", phase4),
    5: ("Audio Devices", phase5),
    6: ("Speech Pipeline", phase6),
    7: ("VSCode Dev", phase7),
    8: ("Deploy App", phase8),
}


def main():
    parser = argparse.ArgumentParser(description="Mini-AI Full Setup")
    parser.add_argument("--from", dest="from_phase", type=int, default=2,
                        help="Start from this phase (default: 2)")
    parser.add_argument("--only", type=int, default=None,
                        help="Run only this phase")
    args = parser.parse_args()

    host, _, _ = get_config()

    print("=" * 60)
    print("  Mini-AI Full Setup")
    print(f"  Target: {host}")
    print("=" * 60)

    c = connect()
    print(f"  Connected to {host}")

    if args.only:
        phases_to_run = [args.only]
    else:
        phases_to_run = [p for p in sorted(PHASES.keys()) if p >= args.from_phase]

    for phase_num in phases_to_run:
        name, func = PHASES[phase_num]
        try:
            c = func(c)
        except SystemExit:
            print(f"\n*** Phase {phase_num} ({name}) FAILED — aborting ***")
            print(f"  Fix the issue and resume with: python setup_all.py --from {phase_num}")
            sys.exit(1)

    # Ensure eth0 route is restored
    restore_eth0_default(c)

    c.close()

    print("\n" + "=" * 60)
    print("  SETUP COMPLETE — ALL PHASES PASSED")
    print("=" * 60)
    print("\n  Run the health check:  python test_pi_state.py")
    print("  Run the pipeline:     ssh mini-ai '~/mini-ai/.venv/bin/python ~/mini-ai/voice_pipeline.py'")
    print("  Connect VSCode:       F1 -> Remote-SSH -> mini-ai -> Open ~/mini-ai")


if __name__ == "__main__":
    main()
