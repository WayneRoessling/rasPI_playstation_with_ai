# DESIGN-MAI-001 — Mini-AI System Architecture

**Document:** DESIGN-MAI-001  
**Project:** Mini-AI  
**Status:** Draft  
**Created:** 2026-04-01  

---

## 1. System Overview

The Mini-AI platform is an offline edge AI node built on Raspberry Pi 5 (16GB). It accepts voice
and image inputs, runs local LLM inference, and outputs synthesized speech responses — all without
sending data to any cloud service.

```
┌─────────────────────────────────────────────────────────┐
│                   Raspberry Pi 5 (16GB)                  │
│                                                         │
│  ┌──────────────┐    ┌───────────────┐   ┌───────────┐ │
│  │  Camera      │    │  Voice Module  │   │  Ollama   │ │
│  │  Logitech    │    │  YB-MAE02-V1.0 │   │  Server   │ │
│  │  USB / UVC   │    │  Mic + Speaker │   │ :11434    │ │
│  └──────┬───────┘    └──────┬────────┘   └─────┬─────┘ │
│         │                  │                   │       │
│  ┌──────▼───────────────────▼───────────────────▼─────┐ │
│  │            voice_pipeline.py  /  mini_ai_app.py    │ │
│  │                                                    │ │
│  │  [USB camera]  ──────────────────► LLaVA 7B       │ │
│  │  [Mic audio]  → Whisper STT → Llama 3B ──────────► │ │
│  │                              LLM response           │ │
│  │                                     │               │ │
│  │                              Piper TTS ──► Speaker  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │         Developer Access (VSCode Remote SSH)        │ │
│  │         Windows PC ←──SSH──→ Pi 5 :22              │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Hardware Architecture

### 2.1 Raspberry Pi 5 (16GB)

| Resource | Allocation |
|----------|-----------|
| RAM | 16GB LPDDR4X |
| CPU | Quad-core Cortex-A76 @ 2.4GHz |
| Storage | 1TB microSD (UHS-I) |
| GPU | VideoCore VII (64MB allocated — remainder for CPU/LLM) |
| I/O | 2× USB 3.0, 2× USB 2.0, 2× CSI, 40-pin GPIO, PCIe 2.0 |
| Power | USB-C 5V / 5A (≥25W supply required) |

### 2.2 Camera — Logitech USB Webcam

| Attribute | Value |
|-----------|-------|
| Interface | USB 2.0 (UVC class — plug-and-play) |
| Sensor | Logitech standard (model TBD — confirm with `lsusb`) |
| Driver | uvcvideo (built into kernel) |
| Access method | OpenCV (`cv2.VideoCapture`) via V4L2 |
| Resolution targets | 1920×1080 still; 1280×720@30fps video |
| Device node | `/dev/video0` (confirm with `v4l2-ctl --list-devices`) |

> **Note:** Logitech UVC cameras are plug-and-play on Bookworm — no dtoverlay or driver install needed.

### 2.3 Voice Module — Yahboom YB-MAE02-V1.0

| Attribute | Value (TBD — confirm during Phase 5) |
|-----------|--------------------------------------|
| Microphone array | 2-mic PDM/I2S or USB audio class |
| Speaker amplifier | Integrated (likely class-D, 1-2W) |
| Interface | USB audio OR I2S via GPIO 18-21 |
| Driver | USB: UAC (plug-and-play) / I2S: wm8960-soundcard dtoverlay |
| ALSA card name | Identified at runtime with `aplay -l` |

### 2.4 Physical GPIO Pinout (if I2S interface)

```
Pi 5 40-pin GPIO Header
─────────────────────────────────────────────────────────
Physical  GPIO  Function          YB-MAE02 connection
Pin 35    GPIO19 I2S FS  (LRCLK)  → LRCLK
Pin 38    GPIO20 I2S DIN (MISO)   ← DOUT (mic data in)
Pin 40    GPIO21 I2S DOUT(MOSI)   → DIN (speaker data out)
Pin 12    GPIO18 I2S CLK (BCLK)   → BCLK
Pin 02    5V                       → VIN (if module is 5V)
Pin 06    GND                      → GND
─────────────────────────────────────────────────────────
```

> Verify against the YB-MAE02-V1.0 schematic/silkscreen before connecting.

---

## 3. Software Architecture

### 3.1 Stack Layers

```
┌─────────────────────────────────────────────────────────┐
│  Application Layer                                      │
│  voice_pipeline.py — orchestrates all components        │
├─────────────────────────────────────────────────────────┤
│  AI Services Layer                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ Ollama       │  │ Whisper.cpp  │  │ Piper-TTS     │ │
│  │ llava:7b     │  │ base.en GGML │  │ en_US-lessac  │ │
│  │ llama3.2:3b  │  │              │  │               │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
├─────────────────────────────────────────────────────────┤
│  System Services Layer                                  │
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │ V4L2 / OpenCV (UVC)  │  │ ALSA / PulseAudio      │  │
│  └──────────────────────┘  └────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  OS — Raspberry Pi OS Bookworm Lite 64-bit (6.6.x)     │
├─────────────────────────────────────────────────────────┤
│  Hardware — Raspberry Pi 5 SBC                          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Process Flow — Voice Turn

```
User speaks
    │
    ▼
arecord ──► [WAV file] ──► whisper.cpp
                                │
                       [transcript text]
                                │
                                ▼
                        ollama (llama3.2:3b)
                                │
                       [response text]
                                │
                                ▼
                        piper-tts ──► [WAV file] ──► aplay
                                                        │
                                                        ▼
                                                   User hears response
```

### 3.3 Process Flow — Vision Turn

```
User requests image analysis ("What do you see?")
    │
    ▼
cv2.VideoCapture(0).read() ──► [JPEG image]
    │                                  │
    ▼                                  ▼
ollama (llava:7b, image=JPEG)
    │
    ▼
[vision + text response]
    │
    ▼
piper-tts ──► aplay ──► User hears description
```

---

## 4. Model Selection Rationale

### 4.1 Vision + Language: LLaVA 1.6 Mistral 7B (Q4_K_M)

| Property | Value |
|----------|-------|
| Parameters | 7B (Mistral base) |
| Quantization | Q4_K_M (4-bit, K-means) |
| RAM required | ~4.5GB |
| Context window | 32k tokens |
| Vision capability | Yes — supports JPEG/PNG image input |
| Source | Meta / LLaVA team via Ollama |
| Rationale | Only mainstream <10B model with strong vision + text on single inference endpoint |

### 4.2 Fast Text: Llama 3.2 3B (Q4_K_M)

| Property | Value |
|----------|-------|
| Parameters | 3B |
| Quantization | Q4_K_M |
| RAM required | ~2.0GB |
| Tokens/sec on Pi 5 | ~15–25 t/s |
| Rationale | Sub-3 second first-token for low-latency voice exchanges |

### 4.3 STT: Whisper.cpp base.en

| Property | Value |
|----------|-------|
| Model size | ~140MB |
| Accuracy | Good for English speech, quiet environments |
| Latency | 2–4s for 5s audio clip on Pi 5 |
| Upgrade path | `small.en` (244MB) for noisier environments |

### 4.4 TTS: Piper en_US-lessac-medium

| Property | Value |
|----------|-------|
| Model size | ~60MB |
| Voice quality | Natural, conversational |
| Latency | < 500ms synthesis per sentence |
| License | Apache 2.0 |

---

## 5. Memory Budget (16GB Pi 5)

| Component | RAM Usage |
|-----------|-----------|
| OS (Bookworm Lite idle) | ~200–350MB |
| Ollama service | ~150MB |
| LLaVA 7B loaded | ~4,500MB |
| Llama 3.2 3B loaded (concurrent) | ~2,000MB |
| Whisper base.en | ~200MB |
| Piper process | ~100MB |
| OpenCV / V4L2 (USB camera) | ~120MB |
| ALSA / audio buffers | ~20MB |
| OS + misc buffers | ~500MB |
| **Total peak estimate** | **~7,940MB** |
| **Headroom** | **~8,060MB** |

> With 16GB, both models can remain loaded simultaneously — Ollama's `keep_alive` prevents
> eviction between voice turns, eliminating the ~10-second cold-load penalty each turn.

---

## 6. Storage Layout

```
/
├── boot/firmware/config.txt      ← gpu_mem=64 (no camera dtoverlay needed — USB)
├── home/pi/
│   ├── mini-ai/                  ← main project code
│   │   ├── voice_pipeline.py
│   │   ├── .venv/
│   │   └── .vscode/settings.json
│   ├── whisper.cpp/
│   │   ├── main                  ← compiled binary
│   │   └── models/ggml-base.en.bin
│   ├── piper-voices/
│   │   └── en_US-lessac-medium.onnx
│   ├── tests/
│   │   ├── camera/
│   │   └── audio/
│   └── yahboom/MAE02/            ← vendor driver repo (if needed)
└── usr/share/ollama/.ollama/
    └── models/                   ← LLaVA + Llama3.2 GGUF blobs
        (~6.5GB total)
```

---

## 7. Network Architecture

```
[Router / Switch]
      │
      ├── Ethernet ─── Raspberry Pi 5  (192.168.x.y  / mini-ai.local)
      │
      └── Wi-Fi ─────── Windows PC     (192.168.x.z)
                              │
                        VSCode Remote SSH ──► Pi 5 :22
                        Browser (Ollama API) ── Pi 5 :11434
```

The Pi binds Ollama to `0.0.0.0:11434` allowing:
- Direct `curl` API calls from Windows for testing
- Future integration with other devices on the LAN

---

## 8. Development Environment

| Tool | Purpose | Location |
|------|---------|----------|
| VSCode (Windows) | IDE | Windows workstation |
| Remote-SSH extension | Connect to Pi | VSCode marketplace |
| Python extension | Python IntelliSense | VSCode (remote install) |
| Pylance extension | Type checking | VSCode (remote install) |
| Ruff extension | Linting/formatting | VSCode (remote install) |
| Python 3.11 venv | Isolated deps | `/home/pi/mini-ai/.venv/` |

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| USB camera not detected | Low | Low | Check `lsusb` and `v4l2-ctl --list-devices`; try different USB port |
| YB-MAE02 uses non-standard I2S codec | Medium | Medium | Check Yahboom GitHub for driver script |
| LLM too slow for comfortable voice UX | Low | Medium | Switch LLaVA to llama3.2:3b for text-only turns |
| Pi 5 thermal throttling under sustained LLM load | Medium | Medium | Add active cooling (Pimoroni or official fan) |
| Whisper STT quality poor in noisy environment | Medium | Medium | Upgrade to `small.en` model; add noise gate |
| 1TB microSD write speed bottleneck | Low | Low | Sequential writes only; no random I/O during inference |

---

## 10. Future Expansion Options

| Feature | Notes |
|---------|-------|
| Wake word detection | Add `openWakeWord` or `Porcupine` before the Whisper step |
| Larger model (13B) | Pi 5 16GB can handle Mistral 13B Q4_K_M (~8GB) without concurrent loading |
| NVMe boot drive | Pi 5 PCIe 2.0 port supports M.2 HATs — ~10x faster storage for model loads |
| Second camera | Add a second USB webcam or use a Pi CSI camera for dual-view |
| Web UI | Run Ollama Web UI or Open WebUI on the Pi for browser-based chat |
| MQTT / Home Assistant | Publish LLM responses to home automation broker |
