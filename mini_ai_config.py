"""Mini-AI runtime configuration — model presets, voices, and persistent user choice.

Presets bundle a (text_model, vision_model) pair under a friendly name so
the user can swap performance/quality tradeoffs from a single picker.

Voice profiles map a friendly key to a Piper TTS voice file on disk.

Volume gain is a multiplier applied via ffmpeg after Piper synthesis,
on top of the ALSA hardware volume (which should be set via amixer).

Persistent state lives at ~/.config/mini-ai/config.json. The picker writes
to it; voice_pipeline.py reads from it on startup. Environment variables
MINI_AI_TEXT_MODEL / MINI_AI_VISION_MODEL / MINI_AI_VOICE / MINI_AI_VOLUME
override the file (useful for ad-hoc testing without touching the saved
choice).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict


# ── Presets ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Preset:
    key: str           # internal id, also written to config.json
    label: str         # short name shown in the picker
    text_model: str    # ollama model tag for text generation
    vision_model: str  # ollama model tag for image-grounded chat
    description: str   # one-liner shown in the picker

    def to_dict(self) -> dict:
        return asdict(self)


PRESETS: list[Preset] = [
    Preset(
        key="tiny",
        label="TINY (lightning fast)",
        text_model="qwen2.5:0.5b",
        vision_model="moondream",
        description="~2.5GB RAM. Snappy replies, minimal smarts. Best for chitchat.",
    ),
    Preset(
        key="fast",
        label="FAST (recommended)",
        text_model="llama3.2:1b",
        vision_model="moondream",
        description="~3.5GB RAM. Snappy and capable. Good default for most prompts.",
    ),
    Preset(
        key="smart",
        label="SMART (slow but best)",
        text_model="llama3.2:3b",
        vision_model="llava:7b",
        description="~7GB RAM. Best quality, but vision cold-start can be 3-4 min on CPU.",
    ),
]

PRESETS_BY_KEY: dict[str, Preset] = {p.key: p for p in PRESETS}
DEFAULT_PRESET_KEY = "fast"


# ── Voice profiles ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Voice:
    key: str         # internal id, also written to config.json
    label: str       # short name shown in the picker
    file: str        # filename inside ~/piper-voices/ (without .onnx extension)
    gender: str      # F or M (informational)
    accent: str      # US, UK, etc. (informational)
    description: str # one-liner shown in the picker


VOICES: list[Voice] = [
    Voice(
        key="lessac",
        label="Lessac (US female, neutral)",
        file="en_US-lessac-medium",
        gender="F", accent="US",
        description="Clean, neutral US female. Good default for most uses.",
    ),
    Voice(
        key="amy",
        label="Amy (US female, friendly)",
        file="en_US-amy-medium",
        gender="F", accent="US",
        description="Warmer, more conversational US female.",
    ),
    Voice(
        key="ryan",
        label="Ryan (US male, high quality)",
        file="en_US-ryan-high",
        gender="M", accent="US",
        description="High-quality US male. Sounds best but slower to synthesize.",
    ),
    Voice(
        key="alan",
        label="Alan (UK male, news anchor)",
        file="en_GB-alan-medium",
        gender="M", accent="UK",
        description="British male, formal news-anchor style.",
    ),
    Voice(
        key="jenny",
        label="Jenny (UK female, expressive)",
        file="en_GB-jenny_dioco-medium",
        gender="F", accent="UK",
        description="British female, more expressive intonation.",
    ),
]

VOICES_BY_KEY: dict[str, Voice] = {v.key: v for v in VOICES}
DEFAULT_VOICE_KEY = "lessac"

PIPER_VOICES_DIR = os.path.expanduser("~/piper-voices")

# Volume gain (1.0 = no change, 2.0 = +6dB, 4.0 = +12dB).
# Anything above 4.0 will start clipping for loud Piper voices.
DEFAULT_VOLUME_GAIN = 1.5
MIN_VOLUME_GAIN = 0.5
MAX_VOLUME_GAIN = 4.0


# ── Persistent config ─────────────────────────────────────────────────────────

CONFIG_DIR = os.path.expanduser("~/.config/mini-ai")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def _read_config() -> dict:
    """Return the saved config dict, or {} on missing/corrupt file."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_config(updates: dict) -> None:
    """Merge updates into the saved config and persist."""
    cfg = _read_config()
    cfg.update(updates)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def load_preset() -> Preset:
    """Resolve the active model preset from env vars, then config file, then default.

    Environment overrides:
        MINI_AI_PRESET             — preset key (tiny|fast|smart)
        MINI_AI_TEXT_MODEL         — overrides preset.text_model
        MINI_AI_VISION_MODEL       — overrides preset.vision_model
    """
    # 1) Env preset key takes precedence
    env_preset = os.environ.get("MINI_AI_PRESET", "").strip().lower()
    if env_preset and env_preset in PRESETS_BY_KEY:
        preset = PRESETS_BY_KEY[env_preset]
    else:
        # 2) Saved config file
        cfg = _read_config()
        key = cfg.get("preset", DEFAULT_PRESET_KEY)
        if key not in PRESETS_BY_KEY:
            key = DEFAULT_PRESET_KEY
        preset = PRESETS_BY_KEY[key]

    # 3) Per-model env overrides (let advanced users mix-and-match)
    text_override = os.environ.get("MINI_AI_TEXT_MODEL", "").strip()
    vision_override = os.environ.get("MINI_AI_VISION_MODEL", "").strip()
    if text_override or vision_override:
        preset = Preset(
            key=preset.key + "+override",
            label=preset.label + " (overridden)",
            text_model=text_override or preset.text_model,
            vision_model=vision_override or preset.vision_model,
            description=preset.description,
        )

    return preset


def save_preset(preset_key: str) -> None:
    """Persist the chosen model preset to the config file."""
    if preset_key not in PRESETS_BY_KEY:
        raise ValueError(f"Unknown preset: {preset_key!r}. Valid: {list(PRESETS_BY_KEY)}")
    _write_config({"preset": preset_key})


def load_voice() -> Voice:
    """Resolve the active TTS voice from env var, then config file, then default."""
    env_voice = os.environ.get("MINI_AI_VOICE", "").strip().lower()
    if env_voice and env_voice in VOICES_BY_KEY:
        return VOICES_BY_KEY[env_voice]
    cfg = _read_config()
    key = cfg.get("voice", DEFAULT_VOICE_KEY)
    if key not in VOICES_BY_KEY:
        key = DEFAULT_VOICE_KEY
    return VOICES_BY_KEY[key]


def save_voice(voice_key: str) -> None:
    """Persist the chosen voice to the config file."""
    if voice_key not in VOICES_BY_KEY:
        raise ValueError(f"Unknown voice: {voice_key!r}. Valid: {list(VOICES_BY_KEY)}")
    _write_config({"voice": voice_key})


def voice_model_path(voice: Voice) -> str:
    """Absolute path to the .onnx file for a voice."""
    return os.path.join(PIPER_VOICES_DIR, voice.file + ".onnx")


def voice_is_installed(voice: Voice) -> bool:
    """True if both .onnx and .onnx.json exist on disk."""
    onnx = voice_model_path(voice)
    return os.path.exists(onnx) and os.path.exists(onnx + ".json")


def load_volume_gain() -> float:
    """Resolve the software volume gain (1.0 = unity)."""
    env_vol = os.environ.get("MINI_AI_VOLUME", "").strip()
    if env_vol:
        try:
            return _clamp_volume(float(env_vol))
        except ValueError:
            pass
    cfg = _read_config()
    return _clamp_volume(float(cfg.get("volume_gain", DEFAULT_VOLUME_GAIN)))


def save_volume_gain(gain: float) -> None:
    """Persist the volume gain to the config file."""
    _write_config({"volume_gain": _clamp_volume(gain)})


def _clamp_volume(gain: float) -> float:
    return max(MIN_VOLUME_GAIN, min(MAX_VOLUME_GAIN, gain))


if __name__ == "__main__":
    # Quick CLI: print active preset, voice, and volume
    p = load_preset()
    v = load_voice()
    g = load_volume_gain()
    print(f"Active preset: {p.key}")
    print(f"  text:   {p.text_model}")
    print(f"  vision: {p.vision_model}")
    print(f"Active voice: {v.key} ({v.label})")
    print(f"  file:      {voice_model_path(v)}")
    print(f"  installed: {voice_is_installed(v)}")
    print(f"Volume gain: {g}x ({20*__import__('math').log10(g):+.1f} dB)")
