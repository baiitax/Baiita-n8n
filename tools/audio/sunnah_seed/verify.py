"""
Sunnah Seed — render verification.

Reads the rendered stems back off disk and checks that what actually came out
of the synthesizer is what the score asked for:

  * note onsets land on the 16th-note grid at 90 BPM
  * detected pitches are the intended pitches (pentatonic, motif shape)
  * the signature motif "ting - ting - ta-ta - ting + resolve" is really there
  * the chord bed follows the intended progression
  * the arrangement density follows the requested 5-section form

Run:  python verify.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy import signal as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from synth import BPM, LOOP_S, N, SR, SPB, hz  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STEMS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "assets", "audio", "sunnah-seed", "stems"))

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def read_wav(path: str):
    import wave

    with wave.open(path, "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    dtype = {2: "<i2", 3: None, 4: "<i4"}[sw]
    if sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 2**15
    elif sw == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2**31
    else:
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = (a[:, 0] | (a[:, 1] << 8) | (a[:, 2] << 16))
        v = np.where(v >= 2**23, v - 2**24, v)
        x = v.astype(np.float64) / 2**23
    return x.reshape(-1, ch), sr


def load_stem(name: str) -> np.ndarray:
    x, _ = read_wav(os.path.join(STEMS, f"{name}.wav"))
    return x[:, 0] if x.shape[1] == 1 else 0.5 * (x[:, 0] + x[:, 1])


def onset_times(mono: np.ndarray, hop: int = 128, thresh_db: float = 12.0):
    """Spectral-flux onset detection, refined to the sample."""
    f, t, Z = sps.stft(mono, fs=SR, nperseg=1024, noverlap=1024 - hop)
    mag = np.abs(Z)
    flux = np.maximum(0.0, np.diff(mag, axis=1)).sum(axis=0)
    flux = np.concatenate([[0.0], flux])
    # adaptive threshold
    win = int(0.35 * SR / hop) | 1
    med = sps.medfilt(flux, kernel_size=win)
    peaks, _ = sps.find_peaks(flux, height=med * 10 ** (thresh_db / 10.0) + 1e-9,
                              distance=int(0.10 * SR / hop))
    out = []
    for p in peaks:
        # refine to the local max of the high-frequency energy in a 6 ms window
        lo = max(p * hop - hop * 8, 0)
        hi = min(p * hop + hop * 8, mono.shape[0])
        seg = np.abs(np.diff(mono[lo:hi], 2))
        out.append(lo + int(np.argmax(seg)) if seg.size else p * hop)
    return np.array(out, dtype=int)


def pitch_of(mono: np.ndarray, start: int, dur: float = 0.14) -> tuple[float, str, float]:
    """Dominant pitched frequency in a short window -> (Hz, note name, dB)."""
    n = int(dur * SR)
    seg = mono[start : start + n]
    if seg.shape[0] < 512:
        return 0.0, "-", -120.0
    seg = seg * np.hanning(seg.shape[0])
    spec = np.abs(np.fft.rfft(seg, 8 * 8192))
    fr = np.fft.rfftfreq(8 * 8192, 1 / SR)
    band = (fr > 110) & (fr < 2400)
    # parabolic peak refinement around the strongest bin
    k = int(np.argmax(spec * band))
    if 0 < k < spec.shape[0] - 1:
        a, b, c = np.log(spec[k - 1] + 1e-20), np.log(spec[k] + 1e-20), np.log(spec[k + 1] + 1e-20)
        d = 0.5 * (a - c) / (a - 2 * b + c + 1e-20)
    else:
        d = 0.0
    f0 = fr[k] + d * (fr[1] - fr[0])
    midi = int(round(69 + 12 * np.log2(max(f0, 1e-6) / 440.0)))
    name = f"{NAMES[midi % 12]}{midi // 12 - 1}"
    return f0, name, 20 * np.log10(np.max(np.abs(seg)) + 1e-12)


def chroma(mono: np.ndarray, hop_beats: float = 1.0):
    """Beat-synchronous chromagram + RMS, for reading the harmony off the page."""
    rows = []
    for b in range(45):
        s = int(b * SPB)
        e = int((b + hop_beats) * SPB)
        seg = mono[s:e] * np.hanning(e - s)
        spec = np.abs(np.fft.rfft(seg, 4 * 16384))
        fr = np.fft.rfftfreq(4 * 16384, 1 / SR)
        c = np.zeros(12)
        idx = (69 + 12 * np.log2(np.maximum(fr, 1e-6) / 440.0)).round().astype(int) % 12
        sel = (fr > 120) & (fr < 2200)
        np.add.at(c, idx[sel], spec[sel] ** 2)
        c /= c.sum() + 1e-20
        rms = float(np.sqrt(np.mean(seg**2)))
        rows.append((b, c, 20 * np.log10(rms + 1e-12)))
    return rows


def main():
    kal = load_stem("kalimba")
    mar = load_stem("marimba")
    xylo = load_stem("xylophone")
    chi = load_stem("chime")
    pad = load_stem("pad")
    rng_root = os.path.abspath(os.path.join(HERE, "..", "..", "..", "assets", "audio", "sunnah-seed", "spec"))
    os.makedirs(rng_root, exist_ok=True)

    print("=" * 78)
    print("Sunnah Seed theme - render verification")
    print("=" * 78)

    # ------------------------------------------------------------------ notes
    for name, bus in (("kalimba", kal), ("marimba", mar), ("xylophone", xylo), ("chime", chi)):
        on = onset_times(bus, thresh_db=10.0)
        print(f"\n--- {name}: {on.shape[0]} note onsets detected")
        rows = []
        for s in on:
            f0, nm, lvl = pitch_of(bus, s)
            rows.append((s / SPB, f0, nm, lvl))
        # print compactly, 4 per line
        line = []
        for b, f0, nm, lvl in rows:
            line.append(f"{b:6.2f}b {nm:>4s}({f0:6.1f}Hz)")
            if len(line) == 4:
                print("   " + " | ".join(line))
                line = []
        if line:
            print("   " + " | ".join(line))

    # ---------------------------------------------------------- motif check
    print("\n" + "-" * 78)
    print("SIGNATURE MOTIF CHECK (should be the same shape wherever it appears)")
    print("-" * 78)
    EXPECT = {
        "C": ["E5", "G5", "A5", "G5", "E5", "G5"],
        "G": ["D5", "G5", "A5", "G5", "D5", "G5"],
        "F": ["C5", "D5", "E5", "D5", "C5", "E5"],
    }
    # bar 0 in the C mode, played on kalimba at beats 0,1,2,2.5,3,3.5
    events = [(0.0, "a"), (1.0, "b"), (2.0, "c"), (2.5, "d"), (3.0, "e"), (3.5, "r")]
    for bar, chord, bus, label in ((0, "C", kal, "kalimba"), (2, "F", mar, "marimba"),
                                   (8, "F", mar, "marimba")):
        beats = [bar * 4 + o for o, _ in events]
        got = []
        for bt in beats:
            f0, nm, _ = pitch_of(bus, int(bt * SPB), 0.30)
            got.append(nm)
        exp = EXPECT[chord]
        mark = "".join("+" if g == e else "x" for g, e in zip(got, exp))
        print(f"  bar {bar:>2d} ({label:>8s}, {chord}): "
              f"want {' '.join(exp):<24s} got {' '.join(got):<24s} {mark}")

    # ----------------------------------------------------------- harmony
    print("\n" + "-" * 78)
    print("HARMONY (beat-synchronous chroma, strongest 3 pitch classes per bar)")
    print("-" * 78)
    rows = chroma(pad)
    EXPECT_CH = ["C", "G", "F", "C", "C", "G", "F", "C", "F", "G", "C"]
    for bar, (b, c, lvl) in enumerate(rows):
        if b % 4:
            continue
        top = np.argsort(c)[::-1][:3]
        names = " ".join(NAMES[i] for i in top)
        bar_no = b // 4
        want = EXPECT_CH[bar_no] if bar_no < len(EXPECT_CH) else "-"
        print(f"  bar {bar_no:>2d} (beat {b:>2d})  loudest pcs: {names:<12s} "
              f"score says: {want:<2s} pad level {lvl:6.1f} dB")

    # ------------------------------------------------------------ density
    print("\n" + "-" * 78)
    print("ARRANGEMENT DENSITY PER SECTION (note onsets, melody buses only)")
    print("-" * 78)
    mel = kal + mar + xylo
    on = onset_times(mel, thresh_db=10.0)
    sections = [("0-5 s   intro   ", 0.0, 5.0), ("5-10 s  build   ", 5.0, 10.0),
                ("10-20 s MAIN    ", 10.0, 20.0), ("20-25 s breathe ", 20.0, 25.0),
                ("25-30 s return  ", 25.0, 30.0)]
    for label, a, b in sections:
        n = int(np.sum((on / SR >= a) & (on / SR < b)))
        seg = mel[int(a * SR) : int(b * SR)]
        rms = 20 * np.log10(np.sqrt(np.mean(seg**2)) + 1e-12)
        print(f"  {label}  onsets={n:>3d}   melody RMS={rms:6.1f} dB")

    print("\n" + "-" * 78)
    print("DELIVERABLE FILES")
    print("-" * 78)
    base = os.path.abspath(os.path.join(HERE, "..", "..", "..", "assets", "audio", "sunnah-seed"))
    for d in ("master", "stems", "spec"):
        p = os.path.join(base, d)
        if os.path.isdir(p):
            for fn in sorted(os.listdir(p)):
                fp = os.path.join(p, fn)
                print(f"  {d}/{fn:<52s} {os.path.getsize(fp)/1024:8.1f} kB")
    print()


if __name__ == "__main__":
    main()
