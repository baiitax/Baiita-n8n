"""
Sunnah Seed — DSP synthesis engine (loop-safe by construction).

Everything is rendered into *circular* buffers of exactly one loop length, so
note tails, reverb, filter state and modulation all wrap around the loop point
with mathematical continuity.  There is no fade-in, no fade-out and no gap:
the last sample and the first sample are simply neighbours in a ring.

Design constraints (from the brand brief):
  warm / joyful / innocent / playful / peaceful / comforting / memorable
  soft organic instruments only, no heavy bass, no harsh highs, big headroom.
"""

from __future__ import annotations

import re

import numpy as np
from scipy import signal as sps

# --------------------------------------------------------------------------
# Global musical / technical constants
# --------------------------------------------------------------------------

SR = 48_000                      # 48 kHz — video delivery standard
BPM = 90.0
BEAT_S = 60.0 / BPM              # 0.666666... s
LOOP_S = 30.0

N = int(round(SR * LOOP_S))      # 1_440_000 samples — the whole loop
SPB = SR * BEAT_S                # 32_000.0 samples per beat (exact!)

NBEATS = int(round(LOOP_S / BEAT_S))   # 45 beats
NBARS = 11                       # 11 full 4/4 bars ...
PICKUP_BEAT = 44                 # ... plus one extra pickup beat

assert abs(SPB - round(SPB)) < 1e-9, "beat must land on exact sample boundaries"
assert NBEATS == 45 and N == 45 * int(SPB)

TWO_PI = 2.0 * np.pi


# --------------------------------------------------------------------------
# Note names -> frequency
# --------------------------------------------------------------------------

_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NOTE_RE = re.compile(r"^\s*([A-Ga-g])([#b]?)(-?\d)\s*$")


def hz(name: str) -> float:
    """'C5' / 'F#4' / 'Bb3' -> equal-tempered frequency (A4 = 440 Hz)."""
    m = _NOTE_RE.match(name)
    if not m:
        raise ValueError(f"bad note name: {name!r}")
    letter, accidental, octave = m.groups()
    midi = (int(octave) + 1) * 12 + _SEMI[letter.upper()]
    if accidental == "#":
        midi += 1
    elif accidental == "b":
        midi -= 1
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


# --------------------------------------------------------------------------
# Circular buffer helpers
# --------------------------------------------------------------------------


def circ_add(buf: np.ndarray, start: int, sig: np.ndarray) -> None:
    """Add `sig` into circular buffer `buf` at sample `start`, wrapping."""
    n = buf.shape[0]
    length = sig.shape[0]
    if length == 0:
        return
    if length >= n:
        k = length // n
        for i in range(k):
            buf += sig[i * n : (i + 1) * n]
        rem = length - k * n
        if rem:
            buf[:rem] += sig[k * n :]
        return
    s = int(start) % n
    end = s + length
    if end <= n:
        buf[s:end] += sig
    else:
        k = n - s
        buf[s:] += sig[:k]
        buf[: length - k] += sig[k:]


def circ_ramp(n: int, start: float, length: float, atk: float, rel: float, level: float = 1.0):
    """Raised-cosine trapezoid envelope living on the circle."""
    L = int(round(length))
    if L <= 2:
        return np.zeros(max(L, 0))
    atk = float(min(atk, L / 2 - 1))
    rel = float(min(rel, L / 2 - 1))
    env = np.full(L, float(level))
    if atk > 0.5:
        a = int(round(atk))
        env[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    if rel > 0.5:
        r = int(round(rel))
        env[L - r :] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(r) / r)
    return env


def beat(b: float) -> int:
    """Beats -> sample index (beats may be fractional)."""
    return int(round(b * SPB))


# --------------------------------------------------------------------------
# Small DSP utilities
# --------------------------------------------------------------------------


def sos_lowpass(fc: float, order: int = 4):
    return sps.butter(order, fc / (SR / 2), btype="low", output="sos")


def sos_highpass(fc: float, order: int = 4):
    return sps.butter(order, fc / (SR / 2), btype="high", output="sos")


def filt(x: np.ndarray, sos) -> np.ndarray:
    return sps.sosfilt(sos, x)


def filt_periodic(x: np.ndarray, sos) -> np.ndarray:
    """IIR filter that is *exactly* periodic — states pre-warmed on 3 copies."""
    triple = np.concatenate([x, x, x])
    y = sps.sosfilt(sos, triple)
    n = x.shape[0]
    return np.array(y[n : 2 * n])


def bandpass_noise(rng: np.random.Generator, n: int, lo: float, hi: float, order: int = 2):
    x = rng.standard_normal(n)
    b, a = sps.butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return sps.lfilter(b, a, x)


def soft_pan(x: np.ndarray, pan: float):
    """Constant-power pan of a mono signal.  pan in [-1, +1] -> (L, R)."""
    pan = float(np.clip(pan, -1.0, 1.0))
    theta = (pan + 1.0) * (np.pi / 4.0)
    return x * np.cos(theta), x * np.sin(theta)


def db(x: float) -> float:
    return 10.0 ** (x / 20.0)


def scaled_tau(base_tau: float, f: float, ref: float = 523.25, expo: float = 0.42) -> float:
    """Real bars/tines ring shorter as pitch rises."""
    return base_tau * (ref / f) ** expo


# --------------------------------------------------------------------------
# Modal (mallet / tine) synthesis
# --------------------------------------------------------------------------


def modal(
    f: float,
    dur: float,
    partials,
    rng: np.random.Generator,
    attack: float = 0.004,
    stretch: float = 1.0,
) -> np.ndarray:
    """
    Additive struck-resonator model.

    partials: list of (ratio, amplitude, tau_seconds, detune_cents)
    `stretch` > 1 gives a slightly slower-than-exponential (organic) decay.
    """
    n = max(int(round(dur * SR)), 8)
    t = np.arange(n) / SR
    y = np.zeros(n, dtype=np.float64)
    for ratio, amp, tau, cents in partials:
        if amp <= 0.0:
            continue
        fp = f * ratio * 2.0 ** (cents / 1200.0)
        if fp >= SR * 0.45:
            continue
        phase = rng.uniform(0.0, TWO_PI)
        env = np.exp(-t / tau)
        if stretch != 1.0:
            env = env**stretch
        y += amp * env * np.sin(TWO_PI * fp * t + phase)
    if attack > 0:
        a = int(round(attack * SR))
        if a > 1 and a < n:
            y[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    return y


def _mallet_click(rng, vel, dur, lo, hi, tau, amp, out: np.ndarray) -> None:
    """Soft noise transient added into the head of a struck note."""
    n = min(max(int(round(dur * SR)), 8), out.shape[0])
    t = np.arange(n) / SR
    noise = bandpass_noise(rng, n, lo, hi)
    out[:n] += noise * np.exp(-t / tau) * amp * vel


# --- individual instruments -------------------------------------------------


def kalimba(f: float, vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Warm thumb-piano tine: long pure fundamental, glassy upper modes,
    a soft wooden-box 'tok' on the attack."""
    rng = rng or np.random.default_rng(0)
    tau = scaled_tau(1.70, f, expo=0.40)
    partials = [
        (1.000, 1.00, tau, 0.0),
        (2.000, 0.210, tau * 0.34, +5.0),
        (2.013, 0.095, tau * 0.30, -7.0),
        (3.930, 0.075, tau * 0.17, +9.0),
        (5.400, 0.030, tau * 0.10, -12.0),
        (6.860, 0.014, tau * 0.06, +15.0),
    ]
    y = modal(f, tau * 3.4, partials, rng, attack=0.0035, stretch=0.92)
    # wooden box knock
    _mallet_click(rng, vel, 0.055, 400.0, 2600.0, 0.010, 0.030, y)
    return y * vel


def marimba(f: float, vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Rosewood bar + resonator: mellow, fundamental-dominant."""
    rng = rng or np.random.default_rng(0)
    tau = scaled_tau(0.95, f, expo=0.46)
    partials = [
        (1.000, 1.00, tau, 0.0),
        (3.990, 0.190, tau * 0.30, +3.0),
        (9.200, 0.042, tau * 0.10, -6.0),
    ]
    y = modal(f, tau * 3.2, partials, rng, attack=0.005, stretch=0.95)
    # resonator "tube" warmth — a soft low-passed thump at the fundamental
    _mallet_click(rng, vel, 0.070, 120.0, 900.0, 0.016, 0.022, y)
    return y * vel


def xylophone(f: float, vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Soft wooden xylophone — shorter and brighter than the marimba, but
    deliberately rolled off so it never turns piercing."""
    rng = rng or np.random.default_rng(0)
    tau = scaled_tau(0.34, f, expo=0.50)
    partials = [
        (1.000, 1.00, tau, 0.0),
        (2.997, 0.300, tau * 0.42, -4.0),
        (5.950, 0.070, tau * 0.20, +7.0),
    ]
    y = modal(f, tau * 4.0, partials, rng, attack=0.0025, stretch=0.95)
    _mallet_click(rng, vel, 0.040, 700.0, 3400.0, 0.006, 0.028, y)
    return y * vel


def chime(f: float, vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Tiny bell / chime bar accent — inharmonic partials, long soft shimmer."""
    rng = rng or np.random.default_rng(0)
    tau = scaled_tau(1.45, f, expo=0.50)
    partials = [
        (1.000, 1.00, tau, 0.0),
        (2.760, 0.230, tau * 0.30, +2.0),
        (5.404, 0.075, tau * 0.14, -5.0),
        (8.900, 0.022, tau * 0.07, +9.0),
    ]
    y = modal(f, tau * 2.6, partials, rng, attack=0.0022, stretch=0.90)
    return y * vel


# --- percussion -------------------------------------------------------------


def frame_dum(vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Low frame-drum stroke — soft, round, no boom, no sub."""
    rng = rng or np.random.default_rng(0)
    n = int(0.40 * SR)
    t = np.arange(n) / SR
    f_inst = 104.0 + (168.0 - 104.0) * np.exp(-t / 0.040)
    phase = TWO_PI * np.cumsum(f_inst) / SR
    body = np.sin(phase) * np.exp(-t / 0.088)
    skin = filt(rng.standard_normal(n), sos_lowpass(1900.0, 2)) * np.exp(-t / 0.014) * 0.50
    y = body + skin
    y *= 0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.0035, 0, 1))
    return y * vel


def frame_tek(vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Rim / finger stroke — tighter, higher, dry."""
    rng = rng or np.random.default_rng(0)
    n = int(0.17 * SR)
    t = np.arange(n) / SR
    f_inst = 230.0 + (360.0 - 230.0) * np.exp(-t / 0.020)
    phase = TWO_PI * np.cumsum(f_inst) / SR
    body = np.sin(phase) * np.exp(-t / 0.055) * 0.75
    skin = filt(rng.standard_normal(n), sos_lowpass(3200.0, 2)) * np.exp(-t / 0.009) * 0.4
    y = body + skin
    y *= 0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.0025, 0, 1))
    return y * vel


def shaker(vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Extremely light hand-percussion shaker — a soft 'swish', never hissy."""
    rng = rng or np.random.default_rng(0)
    n = int(0.14 * SR)
    t = np.arange(n) / SR
    noise = bandpass_noise(rng, n, 3200.0, 7200.0, order=2)
    attack = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.011, 0, 1))
    env = attack * np.exp(-np.clip(t - 0.011, 0, None) / 0.030)
    return noise * env * vel


def finger_clap(vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Soft finger claps — several micro-offset bursts, heavily rounded off."""
    rng = rng or np.random.default_rng(0)
    n = int(0.20 * SR)
    out = np.zeros(n)
    for offset, gain in ((0.000, 1.00), (0.0055, 0.62), (0.0125, 0.34)):
        s = int(offset * SR)
        m = n - s
        t = np.arange(m) / SR
        burst = filt(rng.standard_normal(m), sos_lowpass(4200.0, 3))
        burst = bandpass_noise(rng, m, 1100.0, 3600.0, order=2) * 0.8 + burst * 0.4
        env = (0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.0022, 0, 1))) * np.exp(
            -np.clip(t - 0.0022, 0, None) / 0.026
        )
        out[s:] += burst * env * gain
    # small warm body
    t = np.arange(n) / SR
    out += np.sin(TWO_PI * 980.0 * t) * np.exp(-t / 0.020) * 0.08
    return out * vel


def wood_tick(vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Tiny wooden tick — playful colour, very quiet."""
    rng = rng or np.random.default_rng(0)
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    y = (
        np.sin(TWO_PI * 1046.0 * t) * np.exp(-t / 0.011) * 0.6
        + np.sin(TWO_PI * 1580.0 * t) * np.exp(-t / 0.007) * 0.35
        + filt(rng.standard_normal(n), sos_lowpass(5000.0, 2)) * np.exp(-t / 0.003) * 0.18
    )
    y *= 0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.0018, 0, 1))
    return y * vel


def frame_jingle(vel: float = 1.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """The whisper of riq/daf jingles on a frame-drum hit (kept very low so it
    never becomes a harsh high-frequency element)."""
    rng = rng or np.random.default_rng(0)
    n = int(0.19 * SR)
    t = np.arange(n) / SR
    noise = bandpass_noise(rng, n, 3600.0, 9000.0, order=2)
    env = (0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.0018, 0, 1))) * np.exp(-t / 0.030)
    return noise * env * vel


# --------------------------------------------------------------------------
# Warm airy pad — built from loop-periodic sinusoids
# --------------------------------------------------------------------------


class PadVoice:
    """A single pad note.  Its frequency is snapped to a multiple of 1/LOOP_S
    so the oscillator completes an integer number of cycles per loop: the pad
    is therefore *exactly* periodic and the loop point is mathematically
    invisible in the sustained layer."""

    def __init__(self, freq: float, detune_cents: float, harmonic_amps, lfo_depth=0.0, lfo_cycles=1):
        self.f = round(freq * LOOP_S) / LOOP_S
        self.det = detune_cents
        self.harmonics = harmonic_amps
        self.lfo_depth = lfo_depth
        self.lfo_cycles = max(int(round(lfo_cycles)), 1)

    def render(self, start: int, length: int, phase0: float = 0.0) -> np.ndarray:
        """Oscillator over `length` samples beginning at circular index `start`.

        Frequencies are integer multiples of 1/LOOP_S, so advancing the index
        modulo N keeps the phase exactly consistent with the true periodic
        signal: the segment is a faithful slice of a perfectly loopable wave.
        """
        idx = (np.arange(length) + int(start)) % N
        t = idx / SR
        y = np.zeros(length)
        for k, amp in enumerate(self.harmonics, start=1):
            if amp <= 0.0:
                continue
            f = self.f * k * 2.0 ** (self.det / 1200.0)
            if f >= SR * 0.45:
                continue
            y += amp * np.sin(TWO_PI * f * t + phase0 * k)
        if self.lfo_depth > 0.0:
            y *= 1.0 + self.lfo_depth * np.sin(
                TWO_PI * self.lfo_cycles * t / LOOP_S + phase0 * 0.5
            )
        return y


def air_layer(env: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Very quiet breathy high band that gives the pad its 'airy' quality.
    Band-limited noise filtered circularly -> still perfectly loop-safe."""
    noise = rng.standard_normal(N)
    b, a = sps.butter(2, [1800.0 / (SR / 2), 6200.0 / (SR / 2)], btype="band")
    shaped = sps.lfilter(b, a, noise)
    # circular (hence seamless) smoothing of the noise floor
    padded = np.concatenate([shaped, shaped, shaped])
    sm = sps.sosfilt(sos_lowpass(90.0, 2), padded)[N : 2 * N]
    sm = sm / (np.max(np.abs(sm)) + 1e-12)
    return sm * env


# --------------------------------------------------------------------------
# Reverb — circular convolution, so the tail wraps the loop point perfectly
# --------------------------------------------------------------------------


def make_ir(
    rt60: float,
    seed: int,
    damp_hz: float,
    hp_hz: float = 200.0,
    predelay_ms: float = 18.0,
    er_level: float = 0.55,
) -> np.ndarray:
    """Warm, soft, slightly damped impulse response."""
    rng = np.random.default_rng(seed)
    n = int(rt60 * 1.6 * SR)
    t = np.arange(n) / SR
    env = np.exp(-6.9078 * t / rt60)
    env *= 1.0 - np.exp(-t / 0.0018)
    y = rng.standard_normal(n) * env
    # diffuse first, then damp highs so the tail is warm, never bright
    y = sps.sosfilt(sos_lowpass(damp_hz, 4), y)
    y = sps.sosfilt(sos_highpass(hp_hz, 2), y)
    y /= np.max(np.abs(y)) + 1e-12
    # sparse early reflections for a sense of real space
    for i, (ms, g) in enumerate(
        ((7.0, 0.50), (13.0, 0.38), (19.5, 0.30), (27.0, 0.22), (36.0, 0.15), (47.0, 0.10))
    ):
        s = int(ms * SR)
        if s < n:
            y[s] += g * er_level * (1.0 if i % 2 == 0 else -1.0)
    # pre-delay
    pre = int(predelay_ms * SR)
    y = np.concatenate([np.zeros(pre), y])
    y /= np.sqrt(np.sum(y**2)) + 1e-12      # unit energy
    return y


def circ_convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """Circular convolution of a periodic signal with an IR -> seam-free tail."""
    n = x.shape[0]
    m = min(ir.shape[0], n)
    h = np.zeros(n)
    h[:m] = ir[:m]
    return np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(h), n)


# --------------------------------------------------------------------------
# WAV writer (RIFF + `smpl` loop chunk so DAWs/NLEs see the loop points)
# --------------------------------------------------------------------------


def _quantize(x: np.ndarray, bits: int, dither: bool, rng: np.random.Generator,
              dither_pattern: np.ndarray | None = None) -> bytes:
    peak = float(2 ** (bits - 1))
    if dither_pattern is not None:
        x = x + dither_pattern * (1.0 / peak)
    elif dither:
        x = x + (rng.random(x.shape) - rng.random(x.shape)) * (1.0 / peak)
    q = np.clip(np.round(x * peak), -peak, peak - 1).astype(np.int32)
    if bits == 16:
        return q.astype("<i2").tobytes()
    # 24-bit: little-endian, exactly 3 bytes per sample
    u = np.ascontiguousarray((q & 0xFFFFFF).astype("<u4").view(np.uint8).reshape(-1, 4))
    return u[:, :3].copy().tobytes()


def write_wav(
    path: str,
    audio: np.ndarray,
    sr: int = SR,
    bits: int = 24,
    dither: bool = True,
    seed: int = 7,
    loop: bool = False,
    comment: str = "",
):
    """
    Minimal RIFF/WAVE writer with an optional `smpl` chunk marking the loop
    start/end, plus a `cue ` chunk, so audio editors (Reaper, Premiere, Resolve,
    Audition, Logic…) can loop the file bar-perfectly.
    """
    import struct

    assert bits in (16, 24)
    x = np.asarray(audio, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    frames = x.shape[0]
    channels = x.shape[1]
    rng = np.random.default_rng(seed)
    if dither and loop:
        # Periodic dither: one period of TPDF noise, re-used for every cycle.
        # This keeps even the noise floor bit-exactly loopable.
        n = frames * channels
        pat = (rng.random(n) - rng.random(n))
        pcm = _quantize(x.reshape(-1), bits, dither=False, rng=rng, dither_pattern=pat)
    else:
        pcm = _quantize(x.reshape(-1), bits, dither, rng)

    block_align = channels * (bits // 8)
    byte_rate = sr * block_align
    fmt = struct.pack(
        "<HHIIHH", 1, channels, sr, byte_rate, block_align, bits
    )
    chunks = [b"fmt ", struct.pack("<I", len(fmt)), fmt]

    if loop:
        # --- cue chunk: one cue point at the start of the data -------------
        cue = struct.pack("<I", 1)                                   # dwCuePoints
        cue += struct.pack("<II4sIII", 0, 0, b"data", 0, 0, 0)       # the point
        chunks += [b"cue ", struct.pack("<I", len(cue)), cue]

        # --- smpl chunk: a forward loop over the whole file ---------------
        # 9 header DWORDs + 6 DWORDs per loop = 60 bytes for one loop.
        man = struct.pack(
            "<" + "I" * 15,
            0,                # dwManufacturer
            0,                # dwProduct
            1_000_000 // sr,  # dwSamplePeriod (nanoseconds per sample)
            60,               # dwMIDIUnityNote (C5)
            0,                # dwMIDIPitchFraction
            0,                # dwSMPTEFormat
            0,                # dwSMPTEOffset
            1,                # cSampleLoops
            0,                # cbSamplerData
            0,                #   loop dwIdentifier
            0,                #   loop dwType = 0 (forward)
            0,                #   loop dwStart
            frames,           #   loop dwEnd
            0,                #   loop dwFraction
            0,                #   loop dwPlayCount (0 = infinite)
        )
        assert len(man) == 60, len(man)
        chunks += [b"smpl", struct.pack("<I", len(man)), man]

    if comment:
        payload = comment.encode("ascii", "replace") + b"\x00"
        if len(payload) % 2:
            payload += b"\x00"
        chunks += [b"ICMT", struct.pack("<I", len(payload)), payload]

    data_size = len(pcm)
    chunks += [b"data", struct.pack("<I", data_size), pcm]

    body = b"".join(chunks)
    riff = b"WAVE" + body
    with open(path, "wb") as fh:
        fh.write(b"RIFF")
        fh.write(struct.pack("<I", len(riff)))
        fh.write(riff)


# --------------------------------------------------------------------------
# Master bus processing (all periodic-safe)
# --------------------------------------------------------------------------


def mid_side(stereo: np.ndarray, width: float) -> np.ndarray:
    m = 0.5 * (stereo[:, 0] + stereo[:, 1])
    s = 0.5 * (stereo[:, 0] - stereo[:, 1]) * width
    return np.stack([m + s, m - s], axis=1)


def resample_periodic(x: np.ndarray, up: int, down: int, pad: int = 8192) -> np.ndarray:
    """
    Sample-rate conversion that preserves *exact* periodicity.

    Naive resampling zero-pads the ends, which manufactures a discontinuity at
    the loop point.  Here the signal is wrapped around itself before filtering,
    so the polyphase FIR sees the true periodic continuation.
    """
    n = x.shape[0]
    ext = np.concatenate([x[-pad:], x, x[:pad]], axis=0)
    y = sps.resample_poly(ext, up, down, axis=0)
    lp = int(round(pad * up / down))
    n_out = int(round(n * up / down))
    out = y[lp : lp + n_out]
    if out.shape[0] < n_out:                       # rare off-by-one rounding
        out = np.concatenate([out, y[lp + n_out : lp + n_out + (n_out - out.shape[0])]])
    return out


def peak_dbfs(x: np.ndarray) -> float:
    return 20.0 * np.log10(max(float(np.max(np.abs(x))), 1e-12))


def true_peak_dbfs(x: np.ndarray, oversample: int = 8) -> float:
    """Approximate ITU-R BS.1770 true peak by oversampling."""
    y = sps.resample_poly(x, oversample, 1, axis=0)
    return peak_dbfs(y)
