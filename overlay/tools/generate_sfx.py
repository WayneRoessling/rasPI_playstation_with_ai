"""Procedurally generate the 10 universal SFX WAVs for the CH358 module.

Reads the spec from overlay/canonical/sfx_bank.yaml and writes 10 WAV files
to the output directory (default: overlay/dev_assets/sfx_preview/).

The same files are then copied onto the CH358 TF card via micro-USB.
The simulator also reads from the same output directory for in-browser preview.

Usage:
    python overlay/tools/generate_sfx.py
    python overlay/tools/generate_sfx.py --out /tmp/sfx --sample-rate 16000

Requires:
    pip install numpy pyyaml
"""

from __future__ import annotations

import argparse
import math
import sys
import wave
from pathlib import Path

try:
    import numpy as np
except ImportError:
    sys.exit("numpy required: pip install numpy")

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required: pip install pyyaml")


OVERLAY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BANK = OVERLAY_ROOT / "canonical" / "sfx_bank.yaml"
DEFAULT_OUT = OVERLAY_ROOT / "dev_assets" / "sfx_preview"


# ── Generator primitives ────────────────────────────────────────────────────


def envelope(samples: int, points: list) -> np.ndarray:
    """Piecewise-linear envelope. points = [(time_fraction, amplitude), ...]"""
    if not points:
        return np.ones(samples, dtype=np.float32)
    fractions = np.array([p[0] for p in points], dtype=np.float32)
    amps = np.array([p[1] for p in points], dtype=np.float32)
    ts = np.linspace(0.0, 1.0, samples, dtype=np.float32)
    return np.interp(ts, fractions, amps).astype(np.float32)


def waveform(kind: str, n: int, phase: np.ndarray) -> np.ndarray:
    if kind == "sine":
        return np.sin(phase).astype(np.float32)
    if kind == "square":
        return np.sign(np.sin(phase)).astype(np.float32)
    if kind == "sawtooth":
        return (2.0 * ((phase / (2 * np.pi)) % 1.0) - 1.0).astype(np.float32)
    if kind == "triangle":
        f = (phase / (2 * np.pi)) % 1.0
        return (2.0 * np.abs(2.0 * f - 1.0) - 1.0).astype(np.float32)
    if kind == "white_noise":
        rng = np.random.default_rng(seed=42)
        return rng.uniform(-1.0, 1.0, n).astype(np.float32)
    raise ValueError(f"unknown waveform {kind!r}")


def tone(f_hz: float, duration_ms: int, sr: int, wf: str = "sine") -> np.ndarray:
    n = int(sr * duration_ms / 1000)
    t = np.arange(n) / sr
    return waveform(wf, n, 2 * np.pi * f_hz * t)


def chirp(f_start: float, f_end: float, duration_ms: int, sr: int,
          wf: str = "sine") -> np.ndarray:
    """Linear frequency sweep."""
    n = int(sr * duration_ms / 1000)
    t = np.arange(n) / sr
    T = duration_ms / 1000.0
    # phase = integral of 2*pi*f(t) dt where f(t) = f_start + (f_end-f_start)*t/T
    phase = 2 * np.pi * (f_start * t + (f_end - f_start) * t * t / (2 * T))
    return waveform(wf, n, phase)


def iir_lowpass(x: np.ndarray, cutoff_hz: float, sr: int) -> np.ndarray:
    rc = 1.0 / (2 * math.pi * cutoff_hz)
    dt = 1.0 / sr
    a = dt / (rc + dt)
    y = np.empty_like(x)
    y[0] = x[0] * a
    for i in range(1, len(x)):
        y[i] = y[i - 1] + a * (x[i] - y[i - 1])
    return y.astype(np.float32)


def iir_highpass(x: np.ndarray, cutoff_hz: float, sr: int) -> np.ndarray:
    rc = 1.0 / (2 * math.pi * cutoff_hz)
    dt = 1.0 / sr
    a = rc / (rc + dt)
    y = np.empty_like(x)
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = a * (y[i - 1] + x[i] - x[i - 1])
    return y.astype(np.float32)


def apply_filter(x: np.ndarray, spec: str, sr: int) -> np.ndarray:
    if not spec:
        return x
    parts = spec.split("_")
    kind = parts[0]
    if kind == "lowpass":
        return iir_lowpass(x, float(parts[1]), sr)
    if kind == "highpass":
        return iir_highpass(x, float(parts[1]), sr)
    if kind == "bandpass":
        return iir_lowpass(iir_highpass(x, float(parts[1]), sr), float(parts[2]), sr)
    raise ValueError(f"unknown filter {spec!r}")


# ── Type-specific generators ────────────────────────────────────────────────


def gen_chirp_rising(spec, sr):
    return chirp(spec["f_start_hz"], spec["f_end_hz"], spec["duration_ms"],
                 sr, spec.get("waveform", "sine"))


def gen_chirp_falling(spec, sr):
    return chirp(spec["f_start_hz"], spec["f_end_hz"], spec["duration_ms"],
                 sr, spec.get("waveform", "square"))


def gen_tone(spec, sr):
    return tone(spec["f_hz"], spec["duration_ms"], sr,
                spec.get("waveform", "sine"))


def gen_repeated_tone(spec, sr):
    pulse = tone(spec["f_hz"], spec["pulse_ms"], sr,
                 spec.get("waveform", "sine"))
    pulse *= envelope(len(pulse),
                      [(0, 0), (0.1, 1), (0.9, 1), (1.0, 0)])
    gap_n = int(sr * spec["gap_ms"] / 1000)
    silence = np.zeros(gap_n, dtype=np.float32)
    chunks = []
    for i in range(spec["pulse_count"]):
        chunks.append(pulse)
        if i < spec["pulse_count"] - 1:
            chunks.append(silence)
    sig = np.concatenate(chunks)
    total = int(sr * spec["duration_ms"] / 1000)
    if len(sig) < total:
        sig = np.concatenate([sig, np.zeros(total - len(sig), dtype=np.float32)])
    return sig[:total]


def gen_klaxon(spec, sr):
    total_n = int(sr * spec["duration_ms"] / 1000)
    alt_n = int(sr * spec["alternation_ms"] / 1000)
    out = np.zeros(total_n, dtype=np.float32)
    wf = spec.get("waveform", "sawtooth")
    high = False
    pos = 0
    while pos < total_n:
        end = min(pos + alt_n, total_n)
        n = end - pos
        f = spec["f_high_hz"] if high else spec["f_low_hz"]
        t = np.arange(n) / sr
        out[pos:end] = waveform(wf, n, 2 * np.pi * f * t)
        high = not high
        pos = end
    return out


def gen_impact_with_tone(spec, sr):
    total_n = int(sr * spec["total_duration_ms"] / 1000)
    noise_n = int(sr * spec["noise_duration_ms"] / 1000)
    out = np.zeros(total_n, dtype=np.float32)
    # Noise impact
    noise = waveform("white_noise", noise_n, np.zeros(noise_n))
    noise = apply_filter(noise, spec.get("noise_filter", ""), sr)
    noise *= envelope(noise_n, [(0.0, 1.0), (1.0, 0.0)])
    out[:noise_n] += noise
    # Tone (possibly chirping) follows
    tone_ms = spec["tone_duration_ms"]
    tone_n = int(sr * tone_ms / 1000)
    f_start = spec["tone_f_hz"]
    f_end = spec.get("tone_f_end_hz", f_start)
    if f_start != f_end:
        tone_sig = chirp(f_start, f_end, tone_ms, sr)
    else:
        tone_sig = tone(f_start, tone_ms, sr)
    if "tone_envelope" in spec:
        tone_sig *= envelope(tone_n, [tuple(p) for p in spec["tone_envelope"]])
    tone_start = max(0, noise_n - int(0.02 * sr))
    tone_end = min(total_n, tone_start + tone_n)
    out[tone_start:tone_end] += tone_sig[: tone_end - tone_start]
    return out


def gen_squelch_chirp(spec, sr):
    total_n = int(sr * spec["total_duration_ms"] / 1000)
    sq_n = int(sr * spec["squelch_duration_ms"] / 1000)
    out = np.zeros(total_n, dtype=np.float32)
    noise = waveform("white_noise", sq_n, np.zeros(sq_n))
    noise = apply_filter(noise, spec.get("squelch_filter", ""), sr)
    noise *= envelope(sq_n,
                      [(0, 0), (0.1, 1.0), (0.7, 0.6), (1.0, 0.0)])
    out[:sq_n] += noise * 0.6
    ch = chirp(spec["chirp_f_start_hz"], spec["chirp_f_end_hz"],
               spec["chirp_duration_ms"], sr)
    ch *= envelope(len(ch), [(0, 0), (0.1, 1.0), (0.8, 0.9), (1.0, 0)])
    ch_start = sq_n
    ch_end = min(total_n, ch_start + len(ch))
    out[ch_start:ch_end] += ch[: ch_end - ch_start]
    return out


def gen_noise_burst(spec, sr):
    n = int(sr * spec["duration_ms"] / 1000)
    sig = waveform(spec.get("waveform", "white_noise"), n, np.zeros(n))
    return apply_filter(sig, spec.get("filter", ""), sr)


def gen_multi_tone_sweep(spec, sr):
    freqs = spec["frequencies_hz"]
    tone_ms = spec["tone_duration_ms"]
    gap_ms = spec["gap_ms"]
    tone_n = int(sr * tone_ms / 1000)
    gap_n = int(sr * gap_ms / 1000)
    pulse_env = envelope(tone_n,
                         [(0, 0), (0.1, 1.0), (0.85, 0.95), (1.0, 0)])
    out = []
    for i, f in enumerate(freqs):
        t = tone(f, tone_ms, sr, spec.get("waveform", "sine"))
        out.append(t * pulse_env)
        if i < len(freqs) - 1:
            out.append(np.zeros(gap_n, dtype=np.float32))
    return np.concatenate(out)


GENERATORS: dict = {
    "chirp_rising": gen_chirp_rising,
    "chirp_falling": gen_chirp_falling,
    "tone": gen_tone,
    "repeated_tone": gen_repeated_tone,
    "klaxon": gen_klaxon,
    "impact_with_tone": gen_impact_with_tone,
    "squelch_chirp": gen_squelch_chirp,
    "noise_burst": gen_noise_burst,
    "multi_tone_sweep": gen_multi_tone_sweep,
}

# Generators that bake their own envelope across multiple sub-segments — skip
# applying the slot-level envelope on top.
SELF_ENVELOPED = {"repeated_tone", "multi_tone_sweep"}


# ── Rendering ───────────────────────────────────────────────────────────────


def render_slot(slot_def: dict, sr: int) -> np.ndarray:
    spec = slot_def["spec"]
    gen = GENERATORS.get(spec["type"])
    if gen is None:
        raise ValueError(
            f"slot {slot_def['slot']}: unknown spec.type {spec['type']!r}")
    sig = gen(spec, sr)
    if "envelope" in spec and spec["type"] not in SELF_ENVELOPED:
        env = envelope(len(sig), [tuple(p) for p in spec["envelope"]])
        sig = sig * env
    gain_db = spec.get("gain_db", 0.0)
    sig = sig * (10.0 ** (gain_db / 20.0))
    return np.tanh(sig).astype(np.float32)


def write_wav(path: Path, signal: np.ndarray, sr: int):
    clipped = np.clip(signal, -1.0, 1.0)
    int16 = (clipped * 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16.tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sample-rate", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    bank = yaml.safe_load(args.bank.read_text(encoding="utf-8"))
    fmt = bank.get("output_format", {})
    sr = args.sample_rate or fmt.get("sample_rate", 22050)
    pattern = fmt.get("filename_pattern", "{slot:02d}.wav")

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"generating {len(bank['slots'])} SFX files into {args.out}/")
    print(f"  sample rate: {sr} Hz   bit depth: 16")
    print()

    for slot_def in bank["slots"]:
        slot = slot_def["slot"]
        sig = render_slot(slot_def, sr)
        fname = pattern.format(slot=slot)
        write_wav(args.out / fname, sig, sr)
        if not args.quiet:
            dur_ms = int(1000 * len(sig) / sr)
            print(f"  {fname}  {slot_def['id']:<22} "
                  f"{slot_def['role']:<8} {dur_ms:>5} ms  "
                  f"{len(sig):>7} samples")

    print()
    print(f"done. copy {args.out}/*.wav onto the CH358 TF card "
          f"via the module's micro-USB port.")


if __name__ == "__main__":
    main()
