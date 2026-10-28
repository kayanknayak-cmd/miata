"""Synthesise the soundtrack from the plan: one struck-bar note per pad hit.

Everything is generated from scratch (modal synthesis + filtered noise), so the
audio is 100% original and Content ID has nothing to match against.

Each hit = tonal body (inharmonic bar modes, per-partial decay)
         + impact tick (the marble click: band-passed noise + glassy ping)
         + equal-power pan from the pad's x position
then the whole mix gets a synthetic stereo room reverb, a high-pass, and a
loudness normalise to about -14 LUFS (YouTube's playback target).
"""
import math
import wave

import numpy as np
from scipy import signal

SR = 48000

# ratios: partial frequency / fundamental; amps: relative level; t60: seconds at A4
TIMBRES = {
    "marimba":  dict(ratios=[1, 3.93, 9.24], amps=[1, 0.25, 0.07], t60=0.9, hf_decay=2.2, octave=0,
                     tick=0.20, thock=0.35, tremolo=0),
    "glass":    dict(ratios=[1, 2.32, 4.25, 6.63], amps=[1, 0.32, 0.16, 0.07], t60=2.4, hf_decay=1.4, octave=1,
                     tick=0.30, thock=0.0, tremolo=0),
    "musicbox": dict(ratios=[1, 5.93, 16.6], amps=[1, 0.22, 0.06], t60=1.7, hf_decay=2.5, octave=1,
                     tick=0.18, thock=0.0, tremolo=0),
    "vibes":    dict(ratios=[1, 4.0, 10.0], amps=[1, 0.22, 0.05], t60=2.8, hf_decay=2.0, octave=0,
                     tick=0.15, thock=0.1, tremolo=5.6),
    "kalimba":  dict(ratios=[1, 5.4, 13.1], amps=[1, 0.14, 0.04], t60=1.3, hf_decay=2.8, octave=0,
                     tick=0.22, thock=0.25, tremolo=0),
    "steelpan": dict(ratios=[1, 2.0, 3.0, 4.02], amps=[1, 0.55, 0.28, 0.12], t60=1.2, hf_decay=1.6, octave=0,
                     tick=0.18, thock=0.15, tremolo=0),
}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _bandnoise(n, lo, hi, rng):
    sos = signal.butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, rng.standard_normal(n))


def strike(pitch, vel, tb, rng):
    """One struck note, mono. vel in 0..1 (mallet hardness and level)."""
    f0 = mtof(pitch + 12 * tb["octave"])
    # lower notes ring longer, higher notes shorter (like a real bar)
    t60 = tb["t60"] * (440.0 / f0) ** 0.35
    n = int(SR * min(6.0, t60 * 1.3 + 0.05))
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, (r, a) in enumerate(zip(tb["ratios"], tb["amps"])):
        f = f0 * r * (1 + rng.uniform(-0.0015, 0.0015) * (k > 0))
        if f > SR * 0.45:
            continue
        # harder hits excite upper modes more; upper modes die faster
        amp = a * (vel ** (1 + 1.2 * k))
        dec = t60 / (r ** (1 / tb["hf_decay"]) if k else 1)
        env = np.exp(-6.91 * t / dec)
        out += amp * env * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi) * (k > 0))
    if tb["tremolo"]:
        out *= 1 - 0.22 * (0.5 + 0.5 * np.sin(2 * np.pi * tb["tremolo"] * t))
    # 1.5 ms attack ramp avoids a DC click; the tick provides the real transient
    a = int(SR * 0.0015)
    out[:a] *= np.linspace(0, 1, a)
    # equal-loudness-ish tilt: lift lows, tame highs
    out *= (440.0 / f0) ** 0.25
    # impact tick: very short band-passed noise + a tiny glassy ping
    tn = int(SR * 0.012)
    tick = _bandnoise(tn, 2500, 9000, rng) * np.exp(-np.arange(tn) / (SR * 0.0018))
    pf = rng.uniform(4800, 7200)
    tick += 0.6 * np.sin(2 * np.pi * pf * np.arange(tn) / SR) * np.exp(-np.arange(tn) / (SR * 0.0035))
    out[:tn] += tb["tick"] * vel * tick
    if tb["thock"]:  # woody body knock under the note
        kn = int(SR * 0.03)
        thock = _bandnoise(kn, 180, 1400, rng) * np.exp(-np.arange(kn) / (SR * 0.006))
        out[:kn] += tb["thock"] * vel * thock
    return out * vel


def reverb_ir(t60, rng, predelay=0.012):
    n = int(SR * t60 * 1.1)
    t = np.arange(n) / SR
    env = np.exp(-6.91 * t / t60)
    sos = signal.butter(1, 5500, btype="low", fs=SR, output="sos")
    ir = np.stack([signal.sosfilt(sos, rng.standard_normal(n)) * env for _ in range(2)])
    pd = int(SR * predelay)
    ir = np.pad(ir, ((0, 0), (pd, 0)))
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


def loudness_normalise(x, target_lufs=-14.0, peak_db=-1.0):
    try:
        import pyloudnorm as pyln
        lufs = pyln.Meter(SR).integrated_loudness(x.T)
        x = x * 10 ** ((target_lufs - lufs) / 20)
    except Exception:  # fallback: RMS-based estimate
        rms = np.sqrt((x ** 2).mean()) + 1e-12
        x = x * (10 ** ((target_lufs + 3) / 20) / rms)
    # soft limiter so peaks never clip
    lim = 10 ** (peak_db / 20)
    return np.tanh(x / lim) * lim


def render(plan, timbre="marimba", out_path="audio.wav", reverb=1.4, wet=0.22, seed=0, half_width=1.55):
    rng = np.random.default_rng(seed)
    tb = TIMBRES[timbre]
    n = int(SR * (plan["duration"] + reverb + 0.5))
    dry = np.zeros((2, n))
    speeds = [p["speed"] for p in plan["pads"]]
    ref = np.percentile(speeds, 80) if speeds else 1
    for p in plan["pads"]:
        vel = float(np.clip(0.55 + 0.45 * p["speed"] / ref, 0.5, 1.0)) * rng.uniform(0.93, 1.0)
        parts = [strike(m, vel / math.sqrt(len(p["pitches"])), tb, rng) for m in p["pitches"]]
        note = np.zeros(max(len(x) for x in parts))
        for x in parts:  # chord notes ring for different lengths
            note[:len(x)] += x
        pan = float(np.clip(p["hit"][0] / half_width, -1, 1)) * 0.6
        lg, rg = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        i = int(p["time"] * SR)
        m = min(len(note), n - i)
        dry[0, i:i + m] += note[:m] * lg
        dry[1, i:i + m] += note[:m] * rg
    ir = reverb_ir(reverb, rng)
    wetsig = np.stack([signal.fftconvolve(dry[c], ir[c])[:n] for c in range(2)])
    mix = (1 - wet) * dry + wet * wetsig * 3.0
    sos = signal.butter(2, 40, btype="high", fs=SR, output="sos")
    mix = signal.sosfilt(sos, mix, axis=1)
    mix = loudness_normalise(mix)
    # short fade at the very end
    f = int(SR * 0.3)
    mix[:, -f:] *= np.linspace(1, 0, f)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype("<i2").tobytes())
    return out_path


if __name__ == "__main__":
    import json
    import sys
    pl = json.load(open(sys.argv[1]))
    render(pl, sys.argv[2] if len(sys.argv) > 2 else "marimba", sys.argv[3] if len(sys.argv) > 3 else "/tmp/a.wav")
