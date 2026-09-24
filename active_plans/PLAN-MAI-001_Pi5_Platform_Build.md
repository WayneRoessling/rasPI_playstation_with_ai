# PLAN-MAI-001 — Raspberry Pi 5 Mini-AI Platform Build

**Plan:** PLAN-MAI-001  
**Project:** Mini-AI  
**Status:** Active — Rev 2 (hardened after card corruption incident)  
**Created:** 2026-04-01  
**Revised:** 2026-04-01  

---

## Objective

Stand up a Raspberry Pi 5 (16GB) as a fully offline, on-device edge AI platform supporting:
- Voice assistant pipeline (wake → STT → LLM → TTS)
- Vision pipeline (camera → multimodal LLM → text/voice response)
- Remote development from Windows via VSCode SSH

---

## Hardware Context

| Item | Spec |
|------|------|
| SBC | Raspberry Pi 5 — 16GB RAM |
| Storage | 1TB microSD (replaces 64GB OEM card) |
| Camera | Logitech USB webcam (UVC class, plug-and-play) |
| Voice I/O | Yahboom YB-MAE02-V1.0 (mic array + speaker) |
| Network | Ethernet (phases 1-4) → Wi-Fi (final) |
| Host PC | Windows workstation with VSCode |

---

## Recommendations & Notes

### Storage
- 1TB microSD is correctly sized: the OS (~3GB) + OS headroom + LLaVA 7B model (~4.5GB GGUF)
  + Whisper base.en model (~140MB) + Piper voice (~60MB) fits easily.
- **Do not** repartition — let the Imager write the full image; Bookworm auto-expands on first boot.

### OS Choice
- **Raspberry Pi OS Bookworm Lite (64-bit)** — correct choice.
- Lite (no desktop) is preferred: saves ~800MB RAM at idle for more LLM headroom.
- Bookworm ships with `libcamera` natively for CSI cameras — no manual camera driver build required in most cases.

### Camera (Logitech USB Webcam)
- Standard Logitech USB webcams are UVC-class devices — fully plug-and-play on Bookworm.
- No `dtoverlay`, no `libcamera`, no ribbon cable — just plug into a USB port.
- Accessed via V4L2 (`/dev/video0`) and OpenCV in Python.
- Frees both CSI-2 ports for future expansion if needed.

### LLM Stack
- **Ollama** is recommended over raw llama.cpp for easier model management.
- **LLaVA 1.6 Mistral 7B (Q4_K_M)** handles BOTH vision and text in one model (~4.5GB VRAM/RAM).
- **Llama 3.2 3B** is kept for low-latency voice-only turns (sub-2-second on Pi 5).
- With 16GB RAM, both models fit simultaneously if you use Ollama's model keep-alive.

### Voice Module (YB-MAE02-V1.0)
- Yahboom's MAE02 series typically exposes as either:
  - A **WM8960-based I2S audio codec** (connected to GPIO 18-21), OR
  - A **USB sound card** (plug-and-play)
- **Action required**: Check the physical module for a USB connector vs. a ribbon-to-GPIO connector.
  The setup steps in Phase 5 cover both paths.
- The Yahboom GitHub / product wiki will have the specific `dtoverlay` or driver install script.

### VSCode Development
- **Remote-SSH** extension on your Windows PC is the correct pattern — you edit files on the Pi
  as if they were local, but nothing heavy runs on Windows.
- A static IP or a `.ssh/config` host alias makes reconnection instant.

---

## Phase Overview

| Phase | Title | Gate Test | Risk Mitigations |
|-------|-------|-----------|-----------------|
| 1 | Flash & First Boot | SSH login succeeds, 935GB disk visible | Imager write+verify completes cleanly |
| 2 | OS Hardening & Updates | New kernel running, tools present | tmux session; kernel upgraded separately; initramfs verified before reboot |
| 3 | Camera — Install & Test | USB camera detected, OpenCV captures frame | UVC plug-and-play; no driver install needed |
| 4 | LLM — Install & Test | Ollama responds (text + vision) | tmux for model downloads; ~6.5GB disk budget pre-verified |
| 5 | Voice Module — Install & Test | `aplay` + `arecord` succeed | USB and I2S paths both documented |
| 6 | Pipeline Integration Test | Voice-in → LLM → voice-out end-to-end | Tested per-component before full pipeline |
| 7 | VSCode Remote Dev Environment | VSCode SSH attaches, Python linting active | Key auth pre-configured |
| 7 | VSCode Remote Dev Environment | VSCode SSH attaches, Python linting active |

---

## Phase 1 — Flash & First Boot

**Duration estimate:** 45–90 min (dominated by write speed to microSD)

> ⚠️ **Lesson learned:** Never interrupt Raspberry Pi Imager mid-write. A partial
> write will corrupt the card exactly the same way a failed upgrade does.

### 1.1 — Configure Raspberry Pi Imager (Windows)

1. Download **Raspberry Pi Imager** from https://www.raspberrypi.com/software/ and install it.
2. Insert the **1TB microSD** into your Windows PC via card reader.
3. Launch Imager:
   - **Choose Device** → `Raspberry Pi 5`
   - **Choose OS** → Raspberry Pi OS (other) → **Raspberry Pi OS Lite (64-bit)**
   - **Choose Storage** → Select the 1TB microSD *(verify the 1TB size — do not pick the wrong drive)*

4. Click **Edit Settings** (the pencil/gear icon) and fill in **exactly** this:

   | Tab | Setting | Value |
   |-----|---------|-------|
   | General | Hostname | `mini-ai-01` |
   | General | Username | `<your-username>` |
   | General | Password | *(the Pi admin password — store in your password manager; the setup scripts read it from `.env` via `MINI_AI_PASS` when needed)* |
   | General | Wi-Fi SSID | *(your network — fill in even if using Ethernet)* |
   | General | Wi-Fi Country | `US` |
   | General | Timezone | `America/New_York` |
   | General | Keyboard | `us` |
   | Services | Enable SSH | ✅ Password authentication |

5. Click **Save**.
6. Click **Yes** to apply OS customisation.
7. Click **Yes** to confirm erase.
8. **Walk away** — do not close or interact with the laptop during the write + verify. It will take 30–60 minutes. Imager will show **"Write Successful"** when done.

### 1.2 — Eject and Boot

1. Click **Continue** in Imager, then safely eject the card from Windows.
2. Insert card into the Pi 5 card slot (contacts facing the board).
3. Connect **Ethernet** cable first — plug it in before power.
4. Plug in USB-C power (5V/5A minimum). The Pi will expand the filesystem and complete cloud-init on first boot. **Wait 2 full minutes before trying SSH.**

### 1.3 — SSH In and Verify

On your Windows PC, run the automated connection script — tell me when the Pi is powered on and I will run it for you. Or manually:

```powershell
# Test passwordless SSH (key was pre-configured in earlier session)
ssh -o StrictHostKeyChecking=no -i "$env:USERPROFILE\.ssh\id_ed25519_mini_ai" <user>@<pi-ip> "echo OK && hostname && uname -r && uptime"
```

Expected output:
```
OK
mini-ai-01
6.12.xx+rpt-rpi-2712
 up X min, ...
```

**Gate Test:** SSH connects, hostname is `mini-ai-01`. ✅

### 1.4 — Push SSH Key

The SSH key was generated in a prior session. I will push it automatically once you confirm the Pi is online.

### 1.5 — Verify Disk Expansion

```bash
df -h /
```

Expected: rootfs showing ~935GB available (full 1TB card expanded). If it shows only ~29GB, run:
```bash
sudo raspi-config --expand-rootfs
sudo reboot
```

---

## Phase 2 — OS Hardening & Updates

**Duration estimate:** 20–40 min  

> ⚠️ **Critical rule:** Every long-running command in this phase runs inside `tmux`.
> This means an SSH disconnect cannot kill the process mid-run — the command keeps
> running on the Pi. **Never hard-reboot until you confirm the step finished.**

### 2.1 — Start a tmux Session

```bash
# Start a persistent session named "setup"
tmux new-session -s setup
```

All commands from here through 2.6 are typed **inside that tmux window**.
If you get disconnected: `ssh mini-ai-ip` then `tmux attach -t setup` to rejoin.

### 2.2 — Update Package Index Only (safe, no disk writes to rootfs yet)

```bash
sudo apt update 2>&1 | tee /tmp/apt_update.log
tail /tmp/apt_update.log
```

Wait for it to finish. Verify the last line says something like `91 packages can be upgraded` — no errors.

### 2.3 — Upgrade Packages (EXCLUDING the kernel)

We separate the kernel from everything else so a failed initramfs rebuild can never
produce a broken boot:

```bash
# Upgrade everything EXCEPT kernel images and headers
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" \
  --without-new-pkgs \
  2>&1 | tee /tmp/apt_upgrade.log

# Confirm it finished with no errors
echo "Exit code: $?"
tail -5 /tmp/apt_upgrade.log
```

Wait for `Exit code: 0`.

### 2.4 — Install Essential Tools

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  tmux git curl wget \
  build-essential cmake pkg-config \
  ffmpeg libopenblas-dev libatlas-base-dev \
  i2c-tools libasound2-dev portaudio19-dev \
  htop vim python3-picamera2 \
  2>&1 | tee /tmp/apt_tools.log

echo "Exit code: $?"
tail -3 /tmp/apt_tools.log
```

Wait for `Exit code: 0`.

### 2.5 — Enable Interfaces (non-interactive raspi-config)

```bash
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0
echo "Interfaces enabled"
```

### 2.6 — Set GPU Memory and Verify Config

```bash
# Set gpu_mem=64 (give most RAM to CPU/LLM)
grep -q '^gpu_mem=' /boot/firmware/config.txt \
  && sudo sed -i 's/^gpu_mem=.*/gpu_mem=64/' /boot/firmware/config.txt \
  || echo 'gpu_mem=64' | sudo tee -a /boot/firmware/config.txt

# Verify
grep gpu_mem /boot/firmware/config.txt
```

### 2.7 — Upgrade the Kernel (separately, with verification)

```bash
# Upgrade only kernel packages
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  linux-image-rpi-2712 linux-headers-rpi-2712 \
  2>&1 | tee /tmp/apt_kernel.log

echo "Exit code: $?"
tail -5 /tmp/apt_kernel.log
```

Look for `update-initramfs: Generating /boot/firmware/initramfs_2712` in the output.
**If you do NOT see that line, do not reboot** — run:
```bash
sudo update-initramfs -u -k all 2>&1 | tee /tmp/initramfs.log
tail -5 /tmp/initramfs.log
```

### 2.8 — Verify initramfs Before Rebooting

```bash
# Both files must exist and be > 10MB
ls -lh /boot/firmware/initramfs_2712 /boot/firmware/initramfs8
```

Expected output — both files **10MB or larger**:
```
-rw-r--r-- 1 root root 11M Apr  1 14:xx /boot/firmware/initramfs_2712
-rw-r--r-- 1 root root 11M Apr  1 14:xx /boot/firmware/initramfs8
```

**If either file is missing or under 1MB — do NOT reboot. Run:**
```bash
sudo update-initramfs -u -k all
ls -lh /boot/firmware/initramfs_2712 /boot/firmware/initramfs8
```

### 2.9 — Autoremove and Reboot

```bash
sudo apt autoremove -y

# Final check before reboot
free -h | grep Mem
df -h /
echo "ALL CLEAR — rebooting"

sudo reboot
```

Wait 90 seconds, then reconnect:
```powershell
# Windows
ssh <user>@<pi-ip>
```

### 2.10 — Gate Test (Post Reboot)

```bash
uname -r        # Should show 6.12.75+rpt-rpi-2712 or newer
free -h         # Should show ~15Gi total
df -h /         # Should show ~935G available
which git ffmpeg htop tmux && echo TOOLS_OK
ls /dev/i2c*    # Should show /dev/i2c-1 etc.
python3 -c "import picamera2; print('picamera2 OK')"
```

**Gate Test:** New kernel running, 15GB RAM, tools present, picamera2 imports. ✅

---

## Phase 3 — Camera Installation & Testing

**Duration estimate:** 10–20 min (USB cameras are plug-and-play)

### 3.1 — Connect and Detect Camera

Plug the Logitech USB webcam into one of the Pi 5's **USB 3.0 ports** (blue ports — faster).

```bash
# Verify USB detection
lsusb | grep -i logitech

# Check V4L2 device nodes
v4l2-ctl --list-devices
```

Expected output:
```
Logitech Webcam (usb-xhci-hcd.1-1):
    /dev/video0
    /dev/video1
```

> **Note:** `/dev/video0` is typically the capture device. `/dev/video1` is metadata.

### 3.2 — Install OpenCV

```bash
# OpenCV for Python — the camera access library
sudo apt-get install -y python3-opencv v4l-utils
python3 -c "import cv2; print('OpenCV', cv2.__version__)"
```

### 3.3 — Capture Still Image Test

```bash
mkdir -p ~/tests/camera

# Quick capture using ffmpeg (no Python needed)
ffmpeg -f v4l2 -video_size 1920x1080 -i /dev/video0 -frames:v 1 ~/tests/camera/test_still.jpg -y

ls -lh ~/tests/camera/test_still.jpg
```

### 3.4 — Check Supported Resolutions

```bash
v4l2-ctl --list-formats-ext -d /dev/video0
```

### 3.5 — Python Camera Test

```bash
cat > ~/tests/camera/test_opencv.py << 'EOF'
import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("FAIL: Cannot open camera")
    exit(1)

# Set resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

ret, frame = cap.read()
cap.release()

if ret:
    cv2.imwrite("/home/<user>/tests/camera/py_test.jpg", frame)
    print(f"SUCCESS: Image captured ({frame.shape[1]}x{frame.shape[0]})")
else:
    print("FAIL: Could not read frame")
    exit(1)
EOF

python3 ~/tests/camera/test_opencv.py
```

**Gate Test:** `lsusb` shows Logitech, `/dev/video0` exists, Python OpenCV captures a non-zero image. ✅

---

## Phase 4 — LLM Installation & Testing

**Duration estimate:** 60–120 min (model download is 4.5GB — depends on internet speed)

### 4.1 — Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version

# Enable Ollama to start on boot
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 4.2 — Configure Ollama for Maximum Performance

```bash
# Set Ollama to use all threads and bind to all interfaces
# (so the Python pipeline can call it via localhost:11434)
sudo nano /etc/systemd/system/ollama.service
```

Add under `[Service]`:
```ini
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 4.3 — Pull Models

```bash
# Vision + language model (LLaVA 7B Q4_K_M — ~4.5GB download)
ollama pull llava:7b

# Fast text-only model for voice turns (~2GB download)
ollama pull llama3.2:3b
```

> **Disk impact:** Both models total ~6.5GB. Stored in `/usr/share/ollama/.ollama/models/`

### 4.4 — Test Text Generation

```bash
ollama run llama3.2:3b "Hello! In one sentence, what is the speed of light?"
```

Expected: Response in 3–8 seconds with the correct answer.

### 4.5 — Test Vision Inference

```bash
# Use the still image captured in Phase 3
ollama run llava:7b \
  "Describe this image briefly." \
  --image ~/tests/camera/test_still.jpg
```

Expected: A text description of what is in the captured image.

### 4.6 — Python Inference Test

```bash
pip3 install ollama --break-system-packages

cat > ~/tests/test_ollama.py << 'EOF'
import ollama

# Test text
response = ollama.chat(
    model='llama3.2:3b',
    messages=[{"role": "user", "content": "What is 2 + 2? Answer in one word."}]
)
print("Text test:", response['message']['content'])

# Test vision (using the still image captured in Phase 3)
import base64
with open("/home/<user>/tests/camera/test_still.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

response = ollama.chat(
    model='llava:7b',
    messages=[{
        "role": "user",
        "content": "Describe this image in one sentence.",
        "images": [img_b64]
    }]
)
print("Vision test:", response['message']['content'])
EOF

python3 ~/tests/test_ollama.py
```

**Gate Test:** Both text and vision responses received successfully. ✅

---

## Phase 5 — Yahboom YB-MAE02-V1.0 Voice Module Installation

**Duration estimate:** 30–60 min

### 5.1 — Identify the Module Interface

Before powering on with the module connected, determine its interface:

**Check A — USB Interface:**
```bash
# Connect module, then:
lsusb
```
Look for entries like: `C-Media Electronics`, `Yahboom`, or `USB Audio Device`

**Check B — I2S/GPIO Interface:**
Inspect the PCB — if it uses a ribbon or 40-pin GPIO header with a WM8960 or similar chip
label, it is I2S.

> **If USB is detected (easiest path):** The module will be `/dev/snd/pcmC1D0c` (recording)
> and `/dev/snd/pcmC1D0p` (playback). Skip to 5.3.

### 5.2 — I2S Configuration (if GPIO-connected module)

```bash
# Install WM8960 driver support (Waveshare/Yahboom common codec)
sudo nano /boot/firmware/config.txt
```

Add:
```ini
# WM8960 audio HAT (Yahboom YB-MAE02 I2S variant)
dtoverlay=wm8960-soundcard
```

If the module uses a different codec, download Yahboom's official install script:
```bash
# Check Yahboom's GitHub for MAE02 setup scripts
git clone https://github.com/yahboom/YB-MAE02.git ~/yahboom/MAE02
cd ~/yahboom/MAE02
# Follow the README instructions in that repo
```

Reboot after any `config.txt` changes: `sudo reboot`

### 5.3 — Verify Audio Devices

```bash
# List recording devices
arecord -l

# List playback devices
aplay -l
```

Expected output: Your Pi's built-in audio + the YB-MAE02 listed as a separate card.

### 5.4 — Test Microphone Recording

```bash
mkdir -p ~/tests/audio

# Record 5 seconds to a WAV file (replace card index X with your YB-MAE02 card number)
arecord -D plughw:X,0 -f cd -t wav -d 5 ~/tests/audio/mic_test.wav

# Play it back to verify
aplay ~/tests/audio/mic_test.wav
```

### 5.5 — Test Speaker Playback

```bash
# Generate a test tone
speaker-test -D plughw:X,0 -t sine -f 440 -l 1
```

### 5.6 — Set Default Audio Device

```bash
# Identify card numbers from aplay -l output, then:
sudo nano /etc/asound.conf
```

```
pcm.!default {
    type asym
    capture.pcm "mic"
    playback.pcm "speaker"
}
pcm.mic {
    type plug
    slave { pcm "hw:CARD=YB-MAE02,DEV=0" }
}
pcm.speaker {
    type plug
    slave { pcm "hw:CARD=YB-MAE02,DEV=0" }
}
```

> Replace `CARD=YB-MAE02` with the card name shown in `aplay -l` output.

**Gate Test:** `arecord` captures voice without error; playback is audible on speaker. ✅

---

## Phase 6 — Speech Pipeline Integration

**Duration estimate:** 45–90 min

### 6.1 — Install Whisper.cpp (Speech-to-Text)

```bash
cd ~
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Build with ARM NEON optimizations for Pi 5
make -j4

# Download the English-optimized model
bash ./models/download-ggml-model.sh base.en

# Test STT with a recorded sample
./main -m models/ggml-base.en.bin -f ~/tests/audio/mic_test.wav
```

Expected: Transcription of your recorded voice in ~1–3 seconds.

### 6.2 — Install Piper TTS (Text-to-Speech)

```bash
pip3 install piper-tts --break-system-packages

# Download a voice model (en_US-lessac-medium is high quality, ~60MB)
mkdir -p ~/piper-voices
cd ~/piper-voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Test TTS
echo "Hello, I am your Raspberry Pi assistant." | \
  python3 -m piper \
  --model ~/piper-voices/en_US-lessac-medium.onnx \
  --output_file ~/tests/audio/tts_test.wav

aplay ~/tests/audio/tts_test.wav
```

### 6.3 — Build the Integration Pipeline

```bash
mkdir -p ~/mini-ai

cat > ~/mini-ai/voice_pipeline.py << 'PIPELINE'
#!/usr/bin/env python3
"""
Mini-AI Voice Pipeline
Voice-in → Whisper STT → Ollama LLM → Piper TTS → Speaker
Vision: USB camera → OpenCV → LLaVA → Piper TTS → Speaker
"""
import subprocess
import tempfile
import os
import base64
import cv2
import ollama

WHISPER_BIN = os.path.expanduser("~/whisper.cpp/main")
WHISPER_MODEL = os.path.expanduser("~/whisper.cpp/models/ggml-base.en.bin")
PIPER_MODEL = os.path.expanduser("~/piper-voices/en_US-lessac-medium.onnx")
AUDIO_CARD = "default"  # Update with your YB-MAE02 card name
CAMERA_INDEX = 0         # /dev/video0


def record_utterance(duration_secs: int = 5) -> str:
    """Record from microphone to a temp WAV file. Returns the file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    subprocess.run([
        "arecord", "-D", AUDIO_CARD,
        "-f", "cd", "-t", "wav", "-d", str(duration_secs), tmp.name
    ], check=True, capture_output=True)
    return tmp.name


def capture_image() -> str:
    """Capture a frame from USB camera. Returns path to JPEG file."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Camera capture failed")
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    cv2.imwrite(tmp.name, frame)
    return tmp.name


def transcribe(wav_path: str) -> str:
    """Transcribe audio using whisper.cpp. Returns the transcript text."""
    result = subprocess.run(
        [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", wav_path, "--no-timestamps", "-otxt"],
        capture_output=True, text=True, check=True
    )
    # whisper.cpp writes a .txt file alongside the input
    txt_path = wav_path.replace(".wav", ".wav.txt")
    if os.path.exists(txt_path):
        text = open(txt_path).read().strip()
        os.unlink(txt_path)
        return text
    return result.stdout.strip()


def ask_llm(prompt: str, image_path: str = None) -> str:
    """Send prompt to Ollama. Includes image for vision turns."""
    if image_path:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        response = ollama.chat(
            model="llava:7b",
            messages=[{"role": "user", "content": prompt, "images": [img_b64]}]
        )
    else:
        response = ollama.chat(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": prompt}]
        )
    return response['message']['content']


def speak(text: str) -> None:
    """Synthesize text to speech and play it."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    subprocess.run(
        ["python3", "-m", "piper",
         "--model", PIPER_MODEL,
         "--output_file", tmp_path],
        input=text, text=True, check=True
    )
    subprocess.run(["aplay", tmp_path], check=True, capture_output=True)
    os.unlink(tmp_path)


VISION_TRIGGERS = ["what do you see", "look at", "describe what", "show me", "camera"]


def run_voice_turn() -> None:
    print("Listening... (5 seconds)")
    wav = record_utterance(5)
    print("Transcribing...")
    user_text = transcribe(wav)
    os.unlink(wav)
    print(f"You said: {user_text}")
    if not user_text.strip():
        speak("I didn't catch that. Please try again.")
        return

    # Check if the user is asking for vision
    image_path = None
    if any(trigger in user_text.lower() for trigger in VISION_TRIGGERS):
        print("Capturing image...")
        image_path = capture_image()

    print("Thinking...")
    response = ask_llm(user_text, image_path=image_path)
    if image_path:
        os.unlink(image_path)
    print(f"Assistant: {response}")
    speak(response)


if __name__ == "__main__":
    print("Mini-AI Voice Pipeline — type Ctrl+C to quit")
    while True:
        try:
            run_voice_turn()
        except KeyboardInterrupt:
            break
PIPELINE

chmod +x ~/mini-ai/voice_pipeline.py
```

### 6.4 — Run Integration Test

```bash
python3 ~/mini-ai/voice_pipeline.py
```

Speak a question aloud. The expected flow:
1. Recording indicator appears
2. Transcript shown on screen
3. LLM response shown on screen
4. Response spoken aloud through YB-MAE02 speaker

**Gate Test:** Voice-in → LLM → voice-out completes end-to-end without errors. ✅

---

## Phase 7 — VSCode Remote Development Environment

**Duration estimate:** 20–30 min

### 7.1 — Set Up SSH Key Authentication (Windows)

On your **Windows PC** in PowerShell:

```powershell
# Generate a key pair if you don't have one
if (-not (Test-Path "$env:USERPROFILE\.ssh\id_ed25519")) {
    ssh-keygen -t ed25519 -C "mini-ai-dev" -f "$env:USERPROFILE\.ssh\id_ed25519" -N ""
}

# Copy the public key to the Pi
type "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh pi@mini-ai.local "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# Test passwordless login
ssh pi@mini-ai.local "echo 'Key auth works'"
```

### 7.2 — Configure SSH Host Alias (Windows)

```powershell
$sshConfig = @"
Host mini-ai
    HostName mini-ai.local
    User pi
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
"@

Add-Content "$env:USERPROFILE\.ssh\config" $sshConfig
```

Verify: `ssh mini-ai` connects without a password prompt.

### 7.3 — Install VSCode Remote-SSH Extension

In VSCode (on your Windows PC):
1. Open Extensions panel (`Ctrl+Shift+X`)
2. Search for **Remote - SSH** (by Microsoft)
3. Install it

### 7.4 — Connect VSCode to the Pi

1. Press `F1` → **Remote-SSH: Connect to Host...**
2. Select **mini-ai** from the list
3. A new VSCode window opens connected to the Pi
4. Open folder: `/home/pi/mini-ai`

### 7.5 — Install Pi-Side VSCode Extensions

Inside the Remote VSCode session, install:
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Ruff** (charliermarsh.ruff) — fast Python linter

### 7.6 — Create Python Virtual Environment

```bash
# On the Pi (can do this in the VSCode integrated terminal)
cd ~/mini-ai
python3 -m venv .venv
source .venv/bin/activate
pip install ollama opencv-python pyaudio
```

Set the VSCode Python interpreter to `/home/pi/mini-ai/.venv/bin/python`.

### 7.7 — Workspace Settings

```bash
mkdir -p ~/mini-ai/.vscode
cat > ~/mini-ai/.vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "/home/pi/mini-ai/.venv/bin/python",
    "python.linting.enabled": true,
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    },
    "files.watcherExclude": {
        "**/__pycache__/**": true,
        "**/.venv/**": true
    }
}
EOF
```

**Gate Test:** VSCode Remote window open, Python extension active, integrated terminal runs
Python in the venv. ✅

---

## Appendix A — Troubleshooting Quick Reference

| Symptom | Check | Fix |
|---------|-------|-----|
| SSH refuses connection | Pi booting? LED activity? | Wait 90s after power-on |
| Camera not detected | USB connected? `lsusb` shows it? | Try a different USB port (prefer USB 3.0 blue ports) |
| Camera detected but black image | Lens cap on? `/dev/video0` exists? | Remove lens cap; check `v4l2-ctl --list-devices` |
| Ollama fails to start | Memory? Disk space? | `free -h`, `df -h` — check available resources |
| Poor LLM performance | CPU throttling? | Check `vcgencmd measure_temp`; ensure active cooling |
| Audio card not found | Module powered? | Check USB connection or GPIO seating |
| Whisper transcription empty | Recording silent? | Test `arecord` manually first (Phase 5.4) |
| **Kernel panic on boot** | **initramfs corrupt or missing** | **Reflash card; use Phase 2's separated kernel upgrade procedure** |
| **"attempted to kill init"** | **dpkg interrupted mid-upgrade** | **Reflash; never hard-reboot during apt upgrade** |
| **SSH disconnected during upgrade** | Upgrade may still be running | **tmux**: `tmux attach -t setup` — check if still running before rebooting |
| **initramfs_2712 less than 10MB** | initramfs build failed | Run `sudo update-initramfs -u -k all` and verify size before rebooting |

---

## Appendix B — Performance Benchmarks (Pi 5 / 16GB Targets)

| Task | Expected Latency |
|------|-----------------|
| Whisper base.en transcription (5s audio) | 2–4 seconds |
| Llama 3.2 3B response (voice turn) | 3–8 seconds |
| LLaVA 7B vision analysis (still image) | 15–40 seconds |
| Piper TTS synthesis + play (sentence) | 1–2 seconds |
| Camera capture (still) | < 1 second |

---

## Appendix C — Model Storage Summary

| Model | Size on Disk | Location |
|-------|-------------|----------|
| Llama 3.2 3B (Q4_K_M) | ~2.0 GB | `/usr/share/ollama/.ollama/models/` |
| LLaVA 7B-v1.6 Mistral (Q4_K_M) | ~4.5 GB | `/usr/share/ollama/.ollama/models/` |
| Whisper base.en | ~140 MB | `~/whisper.cpp/models/` |
| Piper en_US lessac medium | ~60 MB | `~/piper-voices/` |
| **Total** | **~6.8 GB** | |

---

## Completion Criteria

All phases complete when:
- [ ] Phase 1: SSH login confirmed on 1TB card
- [ ] Phase 2: System updated, all interfaces enabled, 15GB+ RAM visible
- [ ] Phase 3: USB camera capturing images via OpenCV and Python
- [ ] Phase 4: Both Ollama models responding (text + vision)
- [ ] Phase 5: YB-MAE02-V1.0 recording and playing audio
- [ ] Phase 6: Full voice pipeline runs end-to-end
- [ ] Phase 7: VSCode Remote SSH connected with Python environment
