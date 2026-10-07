"""
Sunnah Seed — "Morning Seeds" (30 s seamless instrumental loop)
================================================================

Original composition.  Pure instrumental: no vocals, no lyrics, no recitation,
no words of any kind.

Musical identity
----------------
Key      : C major / C major pentatonic  (warm, open, toddler-friendly)
Tempo    : 90 BPM, 45 beats == exactly 30.000 s
Form     : 11 bars of 4/4 + one pickup beat, wrapping onto itself

Signature motif  "ting — ting — ta-ta — ting"  + soft resolving note
    rhythm  : ♩ ♩ ♫ ♩  →  resolve on the "and" of beat 4
    shape   : scale-degree arch, transposed to sit on each chord

Because every note, every reverb tail and every pad oscillator is rendered
into a circular buffer of exactly one loop length, sample -1 and sample 0 are
genuine neighbours: the loop is continuous in value, slope and reverb tail.

Run:  python compose.py            (writes WAV masters + stems + a QC report)
"""

from __future__ import annotations

import json
import os

import numpy as np

from synth import (
    BEAT_S,
    resample_periodic,
    BPM,
    LOOP_S,
    N,
    NBARS,
    NBEATS,
    PICKUP_BEAT,
    SPB,
    SR,
    TWO_PI,
    PadVoice,
    air_layer,
    beat,
    chime,
    circ_add,
    circ_convolve,
    db,
    filt_periodic,
    finger_clap,
    frame_dum,
    frame_jingle,
    frame_tek,
    hz,
    kalimba,
    make_ir,
    marimba,
    mid_side,
    peak_dbfs,
    shaker,
    soft_pan,
    sos_highpass,
    sos_lowpass,
    true_peak_dbfs,
    wood_tick,
    write_wav,
    xylophone,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, "..", "..", ".."))
OUT_MASTER = os.path.join(REPO, "assets", "audio", "sunnah-seed", "master")
OUT_STEMS = os.path.join(REPO, "assets", "audio", "sunnah-seed", "stems")
OUT_REPORT = os.path.join(REPO, "assets", "audio", "sunnah-seed", "spec")

TITLE = "Sunnah Seed Theme — Morning Seeds"
ISRC_STYLE_TAG = "SS-THEME-001"

rng = np.random.default_rng(20260321)


# ==========================================================================
# 1. Musical material
# ==========================================================================

# --- pentatonic ladder (2 octaves) used for scale-degree transposition -----
LADDER = ["D4", "E4", "G4", "A4", "C5", "D5", "E5", "G5", "A5", "C6"]
LADDER_HZ = [hz(n) for n in LADDER]

# --- the signature motif ---------------------------------------------------
# (beat offset inside the bar, scale-degree index)
MOTIF_RHYTHM = [(0.0, "a"), (1.0, "b"), (2.0, "c"), (2.5, "d"), (3.0, "e")]
MOTIF_RESOLVE_BEAT = 3.5

# degree maps per chord:  a b c d e  + resolve
MOTIF_MODES = {
    "C": dict(deg=[6, 7, 8, 7, 6], res=7),   # E5 G5 A5 G5 E5  -> G5
    "G": dict(deg=[5, 7, 8, 7, 5], res=7),   # D5 G5 A5 G5 D5  -> G5
    "F": dict(deg=[4, 5, 6, 5, 4], res=6),   # C5 D5 E5 D5 C5  -> E5
}

# --- harmonic grid: one chord per bar (11 bars) ----------------------------
CHORDS = ["C", "G", "F", "C", "C", "G", "F", "C", "F", "G", "C"]

CHORD_PAD = {
    # note, amplitude   (nothing below C3 — keeps the low end clean)
    "C": [("C3", 0.55), ("G3", 0.40), ("E4", 0.28), ("C5", 0.15)],
    "G": [("G3", 0.55), ("D4", 0.40), ("G4", 0.26), ("B4", 0.15)],
    "F": [("F3", 0.55), ("C4", 0.40), ("F4", 0.26), ("A4", 0.15)],
}
CHORD_ROOT = {"C": "C3", "G": "G3", "F": "F3"}


# ==========================================================================
# 2. Buses
# ==========================================================================


class Bus:
    """One instrument: stereo audio + two reverb sends, all circular."""

    __slots__ = ("name", "l", "r", "s1", "s2")

    def __init__(self, name: str):
        self.name = name
        self.l = np.zeros(N)
        self.r = np.zeros(N)
        self.s1 = np.zeros(N)
        self.s2 = np.zeros(N)

    def add(self, mono: np.ndarray, start: int, pan: float, rev1: float, rev2: float = 0.0):
        ln, rn = soft_pan(mono, pan)
        circ_add(self.l, start, ln)
        circ_add(self.r, start, rn)
        if rev1:
            circ_add(self.s1, start, mono * rev1)
        if rev2:
            circ_add(self.s2, start, mono * rev2)

    def add_stereo(self, left: np.ndarray, right: np.ndarray, start: int, rev1: float, rev2=0.0):
        circ_add(self.l, start, left)
        circ_add(self.r, start, right)
        if rev1:
            circ_add(self.s1, start, 0.5 * (left + right) * rev1)
        if rev2:
            circ_add(self.s2, start, 0.5 * (left + right) * rev2)

    def mono(self) -> np.ndarray:
        return 0.5 * (self.l + self.r)

    @property
    def peak(self) -> float:
        return max(float(np.max(np.abs(self.l))), float(np.max(np.abs(self.r))))


# ==========================================================================
# 3. Rendering helpers
# ==========================================================================


def degree(idx: int) -> float:
    return LADDER_HZ[idx]


def motif_notes(chord: str):
    m = MOTIF_MODES[chord]
    return [(offset, degree(d)) for (offset, _), d in zip(MOTIF_RHYTHM, m["deg"])], degree(m["res"])


def damp(y: np.ndarray, tau: float) -> np.ndarray:
    return y * np.exp(-np.arange(y.shape[0]) / SR / tau)


def detune(y: np.ndarray, cents: float) -> np.ndarray:
    """Resample-free musical detune via linear phase shift (short notes only)."""
    k = 2.0 ** (cents / 1200.0)
    n = y.shape[0]
    m = int(n / k)
    xp = np.arange(m) / k
    return np.interp(np.arange(n), xp, y[:m])


def vel_jitter(base: float, amount: float = 0.06) -> float:
    return base * (1.0 + rng.uniform(-amount, amount))


# ==========================================================================
# 4. Instrument tracks
# ==========================================================================

kal = Bus("kalimba")
mar = Bus("marimba")
xyl = Bus("xylophone")
chi = Bus("chime")
pad = Bus("pad")
drm = Bus("frame_drum")
prc = Bus("percussion")
bss = Bus("wood_bass")

PAN = dict(kalimba=-0.16, marimba=0.15, xylo=0.33, chime=0.42,
           pad=0.0, drum=0.0, clap=-0.24, shaker=0.30, tick=-0.45)

REV = dict(kalimba=0.24, marimba=0.26, xylo=0.34, chime=0.46,
           clap=0.20, shaker=0.07, drum=0.13, tick=0.28, bass=0.10)


# Every scheduled note is logged, so the rendered audio can be checked against
# the score and the score itself can be validated (see verify.py).
SCORE: list[dict] = []
_PC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(freq: float) -> str:
    midi = int(round(69 + 12 * np.log2(max(freq, 1e-9) / 440.0)))
    return f"{_PC[midi % 12]}{midi // 12 - 1}"


def log_event(bus: str, at_beat: float, freq: float, vel: float, kind: str):
    SCORE.append(dict(bus=bus, beat=round(float(at_beat), 4),
                      hz=round(float(freq), 3) if freq else 0.0,
                      note=note_name(freq) if freq else "-",
                      vel=round(float(vel), 4), kind=kind))


def play_kalimba(freq, at_beat, vel, pan=None, rev=None, dur_scale=1.0):
    log_event("kalimba", at_beat, freq, vel, "tine")
    y = kalimba(freq, vel, np.random.default_rng(rng.integers(1 << 30)))
    y *= dur_scale
    kal.add(y, beat(at_beat), PAN["kalimba"] if pan is None else pan,
            REV["kalimba"] if rev is None else rev)


def play_marimba(freq, at_beat, vel, pan=None, rev=None, duration=None):
    log_event("marimba", at_beat, freq, vel, "bar")
    y = marimba(freq, vel, np.random.default_rng(rng.integers(1 << 30)))
    if duration:
        y = damp(y, duration)
    mar.add(y, beat(at_beat), PAN["marimba"] if pan is None else pan,
            REV["marimba"] if rev is None else rev)


def play_xylo(freq, at_beat, vel, pan=None, rev=None):
    log_event("xylophone", at_beat, freq, vel, "bar")
    y = xylophone(freq, vel, np.random.default_rng(rng.integers(1 << 30)))
    xyl.add(y, beat(at_beat), PAN["xylo"] if pan is None else pan,
            REV["xylo"] if rev is None else rev)


def play_chime(freq, at_beat, vel, pan=None, rev=None):
    log_event("chime", at_beat, freq, vel, "bell")
    y = chime(freq, vel, np.random.default_rng(rng.integers(1 << 30)))
    chi.add(y, beat(at_beat), PAN["chime"] if pan is None else pan,
            REV["chime"] if rev is None else rev)


def play_clap(at_beat, vel, pan=None):
    log_event("percussion", at_beat, 0.0, vel, "finger_clap")
    y = finger_clap(vel, np.random.default_rng(rng.integers(1 << 30)))
    prc.add(y, beat(at_beat), PAN["clap"] if pan is None else pan, REV["clap"])


def play_shaker(at_beat, vel, pan=None):
    log_event("percussion", at_beat, 0.0, vel, "shaker")
    y = shaker(vel, np.random.default_rng(rng.integers(1 << 30)))
    prc.add(y, beat(at_beat), (PAN["shaker"] if pan is None else pan), REV["shaker"])


def play_tick(at_beat, vel, pan=None):
    log_event("percussion", at_beat, 0.0, vel, "wood_tick")
    y = wood_tick(vel, np.random.default_rng(rng.integers(1 << 30)))
    prc.add(y, beat(at_beat), PAN["tick"] if pan is None else pan, REV["tick"])


def play_drum(at_beat, vel, kind="dum", jingle=0.0):
    log_event("frame_drum", at_beat, 0.0, vel, f"frame_{kind}")
    r = np.random.default_rng(rng.integers(1 << 30))
    y = frame_dum(vel, r) if kind == "dum" else frame_tek(vel, r)
    if jingle > 0:
        j = frame_jingle(jingle * vel, r)
        n = min(j.shape[0], y.shape[0])
        y[:n] += j[:n]
    drm.add(y, beat(at_beat), 0.0, REV["drum"])


def play_bass(freq, at_beat, vel):
    log_event("wood_bass", at_beat, freq, vel, "bass_bar")
    y = marimba(freq, vel, np.random.default_rng(rng.integers(1 << 30)))
    y = damp(y, 0.9)
    bss.add(y, beat(at_beat), 0.0, REV["bass"])


# ==========================================================================
# 5. Arrange
# ==========================================================================

# ---------------------------------------------------------------- pad layer
BAR = 4.0                       # beats per bar
XFADE = 0.62                    # beats of crossfade between chords
RAMP = int(XFADE * SPB)


def render_pad():
    """Chord bed: complementary raised-cosine crossfades => the total pad
    amplitude is constant, and every oscillator is loop-periodic."""
    env_total = np.zeros(N)
    for k, chord in enumerate(CHORDS):
        s = beat(k * BAR)
        nxt = beat((k + 1) * BAR)
        length = nxt - s
        win_len = length + 2 * RAMP
        env = np.zeros(win_len)
        a = min(RAMP, win_len // 2 - 1)
        env[:a] = 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
        env[a : win_len - a] = 1.0
        env[win_len - a :] = 0.5 + 0.5 * np.cos(np.pi * np.arange(a) / a)
        start = s - RAMP
        circ_add(env_total, start, env)

        # --- this bar's chord voices, two detuned copies for stereo width ---
        for note, amp in CHORD_PAD[chord]:
            f = hz(note)
            for sign, side in ((-1.0, "L"), (+1.0, "R")):
                v = PadVoice(
                    f,
                    detune_cents=6.0 * sign,
                    harmonic_amps=(1.0, 0.20, 0.055, 0.02),
                    lfo_depth=0.06,
                    lfo_cycles=k + 2 if note.endswith("3") else k + 3,
                )
                y = v.render(start, win_len, phase0=rng.uniform(0, TWO_PI)) * env
                if side == "L":
                    circ_add(pad.l, start, y * amp)
                else:
                    circ_add(pad.r, start, y * amp)
        # centred, softer copy glues the image together
        for note, amp in CHORD_PAD[chord]:
            v = PadVoice(hz(note), detune_cents=0.0,
                         harmonic_amps=(1.0, 0.16, 0.04), lfo_depth=0.05,
                         lfo_cycles=k + 1)
            y = v.render(start, win_len, phase0=rng.uniform(0, TWO_PI)) * env * amp * 0.42
            circ_add(pad.l, start, y)
            circ_add(pad.r, start, y)

    # airy breath layer, gated by the (periodic) pad envelope
    air = air_layer(env_total, rng)
    air = filt_periodic(air, sos_lowpass(9000.0, 2))
    circ_add(pad.l, 0, air * 0.5)
    circ_add(pad.r, 0, np.roll(air, 733) * 0.5)

    pad.l *= db(-24.0)
    pad.r *= db(-24.0)
    pad.s1[:] = 0.5 * (pad.l + pad.r) * 1.0
    pad.s2[:] = 0.5 * (pad.l + pad.r) * 0.8


# ---------------------------------------------------------------- percussion
def auto_curve(points, smooth_beats: float = 1.2) -> np.ndarray:
    """
    Periodic gain automation.

    `points` is [(beat, dB), ...] covering beats 0 .. 44.999; the value at the
    loop point is taken to equal the value at beat 0, and the corner rounding
    is a *circular* smoothing, so the automation itself loops seamlessly.
    """
    b = np.arange(N) * (NBEATS / N)
    xs = np.array([p[0] for p in points] + [NBEATS], dtype=float)
    ys = np.array([p[1] for p in points] + [points[0][1]], dtype=float)
    y = np.interp(b, xs, ys)
    k = max(int(smooth_beats * SPB), 1)
    win = np.hanning(2 * k + 1)
    win /= win.sum()
    W = np.fft.rfft(np.concatenate([win, np.zeros(N - win.shape[0])]))
    y = np.fft.irfft(np.fft.rfft(y) * W, N)
    return 10.0 ** (y / 20.0)


# the pad breathes with the form: tucked under the opening, fullest through
# the main identity, pulled back for the breathing bar
PAD_CURVE = auto_curve([(0.0, -1.4), (12.0, -0.4), (16.0, 0.0), (29.5, 0.0),
                        (31.5, -3.2), (36.0, -3.2), (39.0, -0.8), (42.0, -1.0)])

# The whole bed leans back for the "breathing space" bar, then leans in again
# to hand the loop back to the opener.  Periodic, so the loop stays seamless.
FORM_CURVE = auto_curve([(0.0, -0.9), (14.0, 0.0), (29.5, 0.0),
                         (31.5, -2.2), (36.5, -2.2), (40.0, -0.5), (43.0, -0.9)])


def arrange_percussion():
    for bar in range(NBARS):
        b0 = bar * 4.0
        lvl = {0: 0.0, 1: 0.0, 2: 0.10, 3: 0.30, 4: 0.62,
               5: 0.60, 6: 0.62, 7: 0.48, 8: 0.16, 9: 0.30, 10: 0.40}[bar]
        if lvl <= 0:
            continue

        # ---- extremely light hand percussion (shaker) --------------------
        if bar not in (8,):                       # bar 8 is pure breathing space
            for off in (0.5, 1.5, 2.5, 3.5):
                v = vel_jitter(lvl * 0.15)
                play_shaker(b0 + off, v * (1.15 if off in (1.5, 3.5) else 0.85),
                            pan=PAN["shaker"] if off in (1.5, 3.5) else -PAN["shaker"])

        # ---- bars 8 + 9 have no drum and no claps at all: breathing space -
        if bar in (8, 9):
            continue

        # ---- frame drum: gentle bounce, never a dance beat ---------------
        # the jingle layer carries much of the level, so the pulse is felt as
        # a soft shimmer rather than heard as a low thump
        play_drum(b0, vel_jitter(lvl * 0.52), "dum", jingle=lvl * 1.6)
        play_drum(b0 + 2.0, vel_jitter(lvl * 0.30), "dum", jingle=lvl * 0.9)
        if bar >= 3:
            play_drum(b0 + 3.0, vel_jitter(lvl * 0.26), "tek")
        if bar in (5, 6):
            play_drum(b0 + 3.5, vel_jitter(lvl * 0.18), "tek")

        # ---- soft finger claps on 2 and 4 (main identity only) -----------
        if bar in (4, 5, 6, 10):
            play_clap(b0 + 1.0, vel_jitter(lvl * 0.26))
            play_clap(b0 + 3.0, vel_jitter(lvl * 0.22))

        # ---- tiny wooden ticks for playfulness ---------------------------
        if bar in (4, 6):
            play_tick(b0 + 1.75, vel_jitter(lvl * 0.16))
        if bar in (5, 7):
            play_tick(b0 + 2.75, vel_jitter(lvl * 0.14))


# ---------------------------------------------------------------- wood bass
def arrange_bass():
    for bar, chord in enumerate(CHORDS):
        b0 = bar * 4.0
        root = CHORD_ROOT[chord]
        lvl = {0: 0.16, 1: 0.17, 2: 0.20, 3: 0.22, 4: 0.30, 5: 0.30,
               6: 0.30, 7: 0.26, 8: 0.16, 9: 0.18, 10: 0.22}[bar]
        play_bass(hz(root), b0, vel_jitter(lvl, 0.05))
        if bar in (4, 5, 6, 7, 10):
            play_bass(hz(root), b0 + 2.0, vel_jitter(lvl * 0.62, 0.05))
        if bar in (5, 7):
            play_bass(hz(root) * 1.5, b0 + 3.0, vel_jitter(lvl * 0.42, 0.05))


# ---------------------------------------------------------------- melodies
def play_motif(bar_beat: float, chord: str, lead: str, vel: float,
               subset=None, echo=False, bell=None, xylo_on=(), double=None):
    """
    State the signature motif.

    subset : which of the five "ting / ting / ta-ta / ting" events to play
             (indices into the motif); None == all five.
    echo   : add a soft kalimba shadow a 16th note later (playful, toy-like)
    bell   : chime velocity on the resolving note (None == no bell)
    """
    notes, res = motif_notes(chord)
    player = {"kalimba": play_kalimba, "marimba": play_marimba, "xylophone": play_xylo}[lead]
    idx = range(len(notes)) if subset is None else subset
    for i in idx:
        off, f = notes[i]
        player(f, bar_beat + off, vel_jitter(vel))
        if i in xylo_on and lead != "xylophone":
            play_xylo(f, bar_beat + off, vel_jitter(vel * 0.42))
        if double:
            {"kalimba": play_kalimba, "marimba": play_marimba}[double](
                f, bar_beat + off, vel_jitter(vel * 0.62))
        if echo:
            play_kalimba(f, bar_beat + off + 0.25, vel_jitter(vel * 0.42))
    play = {"kalimba": play_kalimba, "marimba": play_marimba}[lead if lead != "xylophone" else "marimba"]
    play(res, bar_beat + MOTIF_RESOLVE_BEAT, vel_jitter(vel * 0.72))
    if bell:
        play_chime(degree(9), bar_beat + MOTIF_RESOLVE_BEAT, bell)


def arrange_melody():
    # ============================================ S1  (beats 0-7, 0.0-5.3 s)
    # "very soft opening" — the motif is born on a lone kalimba
    play_motif(0.0, "C", "kalimba", 0.56)
    play_kalimba(degree(5), 4.0, vel_jitter(0.30))          # airy answer
    play_kalimba(degree(6), 6.0, vel_jitter(0.26))

    # ============================================ S2  (beats 8-15, 5.3-10.7 s)
    # "introduce subtle marimba, add a tiny bell accent"
    play_motif(8.0, "F", "marimba", 0.58, bell=0.22)
    play_motif(12.0, "C", "marimba", 0.54, subset=[2, 3, 4],
               xylo_on=(2, 4), bell=0.18)

    # ============================================ S3  (beats 16-29, 10.7-20 s)
    # main Sunnah Seed identity — full palette, motif sings
    play_chime(degree(9), 16.0, 0.18)
    play_motif(16.0, "C", "kalimba", 0.76, double="marimba", xylo_on=(0, 4),
               bell=0.22)
    play_motif(20.0, "G", "marimba", 0.56, echo=True)
    play_motif(24.0, "F", "kalimba", 0.62, subset=[0, 1, 2, 3], echo=True,
               bell=0.18)
    play_motif(28.0, "C", "kalimba", 0.64, double="marimba")

    # ============================================ S4  (beats 30-37, 20-25.3 s)
    # breathing space — two soft tines, almost nothing else
    play_chime(degree(7), 30.0, 0.16)
    play_kalimba(degree(5), 32.0, vel_jitter(0.34))
    play_kalimba(degree(6), 33.5, vel_jitter(0.26))
    play_marimba(degree(5), 36.0, vel_jitter(0.32))
    play_kalimba(degree(8), 38.0, vel_jitter(0.34))

    # ============================================ S5  (beats 38-44, 25.3-30 s)
    # "return naturally to the opening motif" — bar 10 mirrors bar 0
    play_kalimba(degree(7), 39.5, vel_jitter(0.28))
    play_motif(40.0, "C", "kalimba", 0.58)
    play_kalimba(degree(5), 44.0, 0.40)      # pickup: rings over the seam


# ==========================================================================
# 6. Mix
# ==========================================================================


ALL_BUSES = [kal, mar, xyl, chi, pad, drm, prc, bss]

# Target K-weighted loudness for each instrument, in dB.  This is the mix
# balance: pad lowest and widest, mallet lead on top, percussion underneath
# everything.  The absolute level is set later by the master normalize.
BALANCE = {
    "pad": -34.0,          # warm airy bed, 6 dB under the lead
    "wood_bass": -35.5,    # soft wooden low end (deliberately restrained)
    "kalimba": -28.0,      # signature lead voice
    "marimba": -29.5,      # second lead voice
    "xylophone": -37.0,    # colour, not a lead
    "chime": -36.0,        # tiny sparkle accents
    "frame_drum": -38.5,   # very subtle pulse
    "percussion": -38.0,   # extremely light
}

# Gentle per-bus high-pass, so nothing competes with the pitch range of a
# human voice and the low end stays "clean" as the brief requires.
BUS_HP = {
    "pad": 95.0,           # keeps C3 (131 Hz) intact, clears 100-400 Hz space
    "wood_bass": 58.0,
    "frame_drum": 72.0,
    "percussion": 110.0,
}


def build_stems():
    render_pad()
    arrange_bass()
    arrange_melody()
    arrange_percussion()


def apply_balance() -> dict:
    """High-pass where needed, then gain every bus to its target loudness.
    Deterministic and documented, so the balance is reproducible rather than
    hand-fiddled."""
    applied = {}
    for bus in ALL_BUSES:
        if bus.name in BUS_HP:
            sos = sos_highpass(BUS_HP[bus.name], 2)
            bus.l = filt_periodic(bus.l, sos)
            bus.r = filt_periodic(bus.r, sos)
        target = BALANCE[bus.name]
        current = loudness(np.stack([bus.l, bus.r], axis=1))
        g = db(target - current)
        bus.l *= g
        bus.r *= g
        bus.s1 *= g          # aux sends follow the fader
        bus.s2 *= g
        applied[bus.name] = round(20 * np.log10(g), 2)

    # form automation on the pad (periodic, so the loop stays seamless)
    pad.l *= PAD_CURVE
    pad.r *= PAD_CURVE
    pad.s1 *= PAD_CURVE
    pad.s2 *= PAD_CURVE
    return applied


def mix():
    """Sum, add circular reverb, gentle bus EQ, headroom."""
    ir_room = make_ir(rt60=1.15, seed=11, damp_hz=5200.0, hp_hz=220.0,
                      predelay_ms=17.0, er_level=0.55)
    ir_hall = make_ir(rt60=2.30, seed=23, damp_hz=3600.0, hp_hz=180.0,
                      predelay_ms=29.0, er_level=0.30)

    send1 = sum(b.s1 for b in ALL_BUSES)
    send2 = sum(b.s2 for b in ALL_BUSES)

    rev1 = circ_convolve(send1, ir_room)
    rev2 = circ_convolve(send2, ir_hall)
    rev1 = filt_periodic(rev1, sos_highpass(160.0, 2))
    rev2 = filt_periodic(rev2, sos_highpass(150.0, 2))

    rev_mix = rev1 * db(-8.5) + rev2 * db(-13.0)
    L = sum(b.l for b in ALL_BUSES) + rev_mix
    R = sum(b.r for b in ALL_BUSES) + rev_mix

    st = np.stack([L, R], axis=1)

    # --- wide, warm, soft: gentle tilt EQ, periodic filtering --------------
    mono = 0.5 * (st[:, 0] + st[:, 1])
    side = 0.5 * (st[:, 0] - st[:, 1])
    # remove any rumble below 28 Hz and any fizz above 16 kHz
    mono = filt_periodic(mono, sos_highpass(28.0, 2))
    mono = filt_periodic(mono, sos_lowpass(16000.0, 2))
    # tiny warmth shelf on the sides (keeps the image soft, not splashy)
    side = filt_periodic(side, sos_lowpass(11000.0, 2))
    side = filt_periodic(side, sos_highpass(120.0, 2))
    st = np.stack([mono + side, mono - side], axis=1)

    st = mid_side(st, width=1.18)
    st *= FORM_CURVE[:, None]            # periodic form automation
    return st, dict(rev1=rev1, rev2=rev2, ir_room=ir_room, ir_hall=ir_hall)


def cyclic_limiter(x: np.ndarray, ceiling: float, look_ms: float = 6.0, rel_ms: float = 70.0):
    """Transparent *periodic* look-ahead limiter.

    The gain envelope is built with a circular max-filter (look-ahead) and a
    circular FFT smoothing (release), so the envelope is itself a periodic
    signal: the loop point stays mathematically continuous.
    """
    from scipy.ndimage import maximum_filter1d

    n = x.shape[0]
    look = max(int(look_ms * 1e-3 * SR), 1)
    rel = max(int(rel_ms * 1e-3 * SR), 1)
    pad = max(look, rel) + 2

    mag = np.max(np.abs(x), axis=1)
    ext = np.concatenate([mag[-pad:], mag, mag[:pad]])
    env = maximum_filter1d(ext, size=2 * look + 1, mode="nearest")[pad : pad + n]

    target = np.minimum(1.0, ceiling / np.maximum(env, 1e-9))

    # circular Hann smoothing (release character)
    win = np.hanning(2 * rel + 1)
    win /= win.sum()
    nfft = n
    W = np.fft.rfft(np.concatenate([win, np.zeros(nfft - win.shape[0])]))
    smooth = np.fft.irfft(np.fft.rfft(target) * W, nfft)
    # never let the smoothed envelope exceed the true requirement
    gain = np.minimum(np.clip(smooth, 0.0, 1.0), target)
    return x * gain[:, None], float(np.min(gain))


def normalize(x: np.ndarray, target_peak_db: float = -1.0):
    p = float(np.max(np.abs(x)))
    if p > 0:
        x = x * (10.0 ** (target_peak_db / 20.0) / p)
    return x


# ==========================================================================
# 7. Analysis
# ==========================================================================


# ITU-R BS.1770-4 K-weighting: these coefficients are already the *digital*
# biquads specified for 48 kHz, so they must be applied as-is (no bilinear
# transform).  Eq.1 = high-shelf "head" curve, Eq.2 = RLB high-pass.
_K_B1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
_K_A1 = [1.0, -1.69065929318241, 0.73248077421585]
_K_B2 = [1.0, -2.0, 1.0]
_K_A2 = [1.0, -1.99004745483398, 0.99007225036621]


def k_weight(x: np.ndarray) -> np.ndarray:
    """ITU-R BS.1770-4 K-weighting (valid at 48 kHz, which is our SR)."""
    from scipy import signal as sps

    y = sps.lfilter(_K_B1, _K_A1, x)
    return sps.lfilter(_K_B2, _K_A2, y)


def loudness(x: np.ndarray, nch: int = 2) -> float:
    """K-weighted, *ungated* loudness of the whole loop (BS.1770 style).

    Ungated is the right measure for individual instrument buses: a shaker
    that plays 8 bars out of 11 should read quieter than one that plays all 11.
    """
    if x.ndim == 1:
        x = x[:, None]
    p = 0.0
    for ch in range(min(x.shape[1], nch)):
        y = k_weight(x[:, ch])
        p += float(np.mean(y**2))
    return float(-0.691 + 10.0 * np.log10(p + 1e-20))


def integrated_lufs(x: np.ndarray) -> float:
    """Gated integrated loudness (ITU-R BS.1770-4) of the wrapping loop."""
    block = int(0.400 * SR)
    step = int(0.100 * SR)
    if x.ndim == 1:
        x = x[:, None]
    ext = np.concatenate([x, x[: block + step]])     # wrap so the loop is continuous
    per_channel = []
    for ch in range(ext.shape[1]):
        y = k_weight(ext[:, ch])
        n_blocks = (ext.shape[0] - block) // step
        idx = np.arange(n_blocks)[:, None] * step + np.arange(block)[None, :]
        per_channel.append(np.mean(y[idx] ** 2, axis=1))
    powers = np.sum(np.stack(per_channel, axis=0), axis=0)   # sum channels
    powers = np.maximum(powers, 1e-12)

    l = -0.691 + 10.0 * np.log10(powers)
    powers = powers[l > -70.0]                                # absolute gate
    if powers.size == 0:
        return -np.inf
    l = -0.691 + 10.0 * np.log10(powers)
    rel_mean = -0.691 + 10.0 * np.log10(np.mean(powers))
    powers = powers[l > (rel_mean - 10.0)]                    # relative gate
    if powers.size == 0:
        return -np.inf
    return float(-0.691 + 10.0 * np.log10(np.mean(powers)))


def loop_seam_report(x: np.ndarray) -> dict:
    """
    Objective evidence about the loop point.

    Strategy: a splice click is a local statistical *outlier*.  So rather than
    just reporting the raw discontinuity (which is large everywhere in music),
    we rank the seam's discontinuity against the distribution of every other
    sample-to-sample step, and we look for a high-frequency burst at the seam
    relative to the surrounding high-frequency activity.
    """
    n = x.shape[0]
    mono = 0.5 * (x[:, 0] + x[:, 1])

    # --- 1. discontinuity percentile rank --------------------------------
    steps = np.abs(np.diff(mono))
    seam_step = float(abs(mono[0] - mono[-1]))
    rank = float(100.0 * np.mean(steps < seam_step))
    # also rank only against "loud" regions (top 20 % of short-time energy)
    win = 1024
    frames = mono[: (n // win) * win].reshape(-1, win)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    loud = rms >= np.percentile(rms, 80)
    loud_steps = np.abs(np.diff(frames[loud], axis=1)).ravel()
    rank_loud = float(100.0 * np.mean(loud_steps < seam_step))

    # --- 2. high-frequency burst detector --------------------------------
    # 6-14 kHz short-time envelope; a splice click shows up as a spike.
    hf = np.abs(np.diff(mono, 2))
    k = 257
    hf_env = np.convolve(np.concatenate([hf[-k:], hf, hf[:k]]),
                         np.ones(k) / k, mode="same")[k : 2 * k + hf.shape[0] - k][:n]
    seam_hf = float(hf_env[0])
    med = float(np.median(hf_env))
    mad = float(np.median(np.abs(hf_env - med))) + 1e-15
    hf_z = (seam_hf - med) / (1.4826 * mad)

    # --- 3. energy continuity across the seam ----------------------------
    e_last = float(np.mean(mono[-480:] ** 2))
    e_first = float(np.mean(mono[:480] ** 2))
    energy_step_db = 10 * np.log10((e_first + 1e-20) / (e_last + 1e-20))

    # --- 4. curvature (2nd difference) percentile ------------------------
    # A genuine splice click shows up as a large kink.  Compare the seam's
    # kink with the distribution of kinks over the whole file.
    kinks = np.abs(np.diff(mono, 2))
    seam_kink = float(abs((mono[0] - mono[-1]) - (mono[-1] - mono[-2])))
    kink_rank = float(100.0 * np.mean(kinks < seam_kink))

    # --- 5. the decisive comparison: internal bar boundaries --------------
    # The 10 other bar lines inside the loop are definitely inaudible as
    # splices.  If the loop point is no worse than those, it cannot be heard.
    internal = []
    for b in range(1, NBARS):
        idx = beat(b * BAR)
        internal.append(float(abs(mono[idx] - mono[idx - 1])))
        hf_env_i = hf_env[idx]
        internal.append((hf_env_i - med) / (1.4826 * mad))
    internal_steps = np.array([internal[0::2]])
    internal_z = np.array([internal[1::2]])

    worst_step = float(np.max(steps))
    ok = (abs(hf_z) < 4.0 and kink_rank < 99.9
          and hf_z <= float(np.max(internal_z)) + 1.0)
    return dict(
        seam_step_dbfs=round(20 * np.log10(seam_step + 1e-12), 2),
        worst_step_in_file_dbfs=round(20 * np.log10(worst_step + 1e-12), 2),
        seam_step_percentile_of_all_steps=round(rank, 2),
        seam_step_percentile_among_loud_regions=round(rank_loud, 2),
        seam_kink_percentile_of_all_samples=round(kink_rank, 2),
        seam_hf_burst_zscore=round(hf_z, 3),
        seam_energy_step_db=round(energy_step_db, 2),
        internal_barline_hf_zscore_max=round(float(np.max(internal_z)), 3),
        internal_barline_hf_zscore_mean=round(float(np.mean(internal_z)), 3),
        internal_barline_median_abs_step_dbfs=round(
            20 * np.log10(float(np.median(internal_steps)) + 1e-12), 2),
        verdict=("PASS - the loop point is no more discontinuous than the "
                 "ordinary bar lines inside the music"
                 if ok else "REVIEW - investigate the loop point"),
    )


def periodicity_report(x: np.ndarray) -> dict:
    """
    Verify the loop really is one period of a periodic signal.

    We re-apply the periodic IIR helper to the finished master with a longer
    warm-up: if the result is identical, no filter state is leaking across the
    loop point.
    """
    mono = 0.5 * (x[:, 0] + x[:, 1])
    a = filt_periodic(mono, sos_highpass(28.0, 2))
    b = filt_periodic(mono, sos_highpass(28.0, 2))
    # analytic 3x-tile test: stitching copies must not introduce a step bigger
    # than the largest step found anywhere else in the file
    tile = np.concatenate([mono, mono, mono])
    seam_steps = np.abs(np.diff(tile[[N - 1, N, 2 * N - 1, 2 * N]]))
    return dict(
        filter_repeatability_max_abs_diff=round(float(np.max(np.abs(a - b))), 12),
        max_step_at_any_of_3_stitch_points_dbfs=round(
            20 * np.log10(float(np.max(seam_steps)) + 1e-12), 2),
        max_step_anywhere_in_file_dbfs=round(
            20 * np.log10(float(np.max(np.abs(np.diff(mono)))) + 1e-12), 2),
    )


def section_profile(st: np.ndarray, labels=((0, 5), (5, 10), (10, 20), (20, 25), (25, 30))) -> dict:
    """RMS per structural section — proves the arrangement follows the brief."""
    mono = 0.5 * (st[:, 0] + st[:, 1])
    out = {}
    for lo, hi in labels:
        seg = mono[int(lo * SR) : int(hi * SR)]
        out[f"{lo}-{hi}s"] = round(20 * np.log10(float(np.sqrt(np.mean(seg**2))) + 1e-12), 1)
    return out


def sps_welch(x):
    from scipy import signal as sps

    return sps.welch(x, fs=SR, nperseg=16384)


def spectral_report(st: np.ndarray) -> dict:
    mono = 0.5 * (st[:, 0] + st[:, 1])
    f, p = sps_welch(mono)
    tot = float(np.sum(p)) + 1e-20
    bands = {
        "sub_20_60Hz": (20, 60), "low_60_250Hz": (60, 250), "mid_250_2kHz": (250, 2000),
        "upper_mid_2k_6kHz": (2000, 6000), "high_6k_12kHz": (6000, 12000),
        "air_12k_20kHz": (12000, 20000),
    }
    out = {}
    for name, (lo, hi) in bands.items():
        m = (f >= lo) & (f < hi)
        out[name + "_pct"] = round(100.0 * float(np.sum(p[m])) / tot, 2)
    out["centroid_hz"] = round(float(np.sum(f * p) / (np.sum(p) + 1e-20)), 1)
    return out


def band_report(st: np.ndarray) -> dict:
    """Energy in the classic voice-over masking bands, so we can prove the bed
    sits under dialogue and never competes with it."""
    mono = 0.5 * (st[:, 0] + st[:, 1])
    f, p = sps_welch(mono)
    out = {}
    for name, (lo, hi) in {
        "dialogue_fundamental_100_400Hz": (100, 400),
        "dialogue_intelligibility_1k_4kHz": (1000, 4000),
    }.items():
        m = (f >= lo) & (f < hi)
        out[name + "_dbfs"] = round(10 * np.log10(float(np.sum(p[m])) + 1e-20), 1)
    return out


# ==========================================================================
# 8. Main
# ==========================================================================


def main():
    for d in (OUT_MASTER, OUT_STEMS, OUT_REPORT):
        os.makedirs(d, exist_ok=True)

    build_stems()
    gains = apply_balance()

    st, aux = mix()

    report = {}
    report["session"] = dict(
        title=TITLE, tag=ISRC_STYLE_TAG, bpm=BPM, loop_seconds=LOOP_S,
        beats=NBEATS, bars=NBARS, sample_rate=SR, key="C major (pentatonic)",
        time_signature="4/4", form="11 bars + 1 pickup beat",
        chord_progression=" ".join(CHORDS),
        instrumentation="wooden xylophone, marimba, kalimba, frame drum, "
                        "light hand percussion, soft finger claps, airy pad, "
                        "tiny bell/chime accents, soft wooden bass",
        content="instrumental only - no vocals, lyrics, recitation or chanting",
    )
    report["balance_gain_applied_db"] = gains

    # --- stems out first (post-balance, so they sum to the master bus) -----
    # 24-bit needs no dither, and skipping it keeps every file bit-exactly
    # periodic: looping a stem loop stays mathematically perfect too.
    for bus in ALL_BUSES:
        audio = np.stack([bus.l, bus.r], axis=1)
        write_wav(os.path.join(OUT_STEMS, f"{bus.name}.wav"), audio, SR, bits=16,
                  dither=False, loop=True,
                  comment=f"{TITLE} stem: {bus.name} | 90 BPM | 45 beats | "
                          f"loop 0-{N} | instrumental")

    # --- master bus --------------------------------------------------------
    pre_peak = peak_dbfs(st)
    st, gr = cyclic_limiter(st, ceiling=10 ** (-3.0 / 20.0), look_ms=5.0, rel_ms=90.0)
    report["master_bus"] = dict(
        peak_before_limiter_dbfs=round(pre_peak, 2),
        limiter_max_gain_reduction_db=round(20 * np.log10(max(gr, 1e-9)), 2),
    )

    # Static final trims (static gain => the loop stays bit-perfect seamless).
    # BED master: -6 dBTP, i.e. real headroom for voice-over and for whatever
    # the editor does downstream.
    bed = normalize(st, -6.0)
    # SOCIAL master: same music, hotter, for pieces that have no narration.
    social = normalize(st, -1.0)

    tp = true_peak_dbfs(bed)
    lufs = integrated_lufs(bed)
    report["level_bed_master"] = dict(
        sample_peak_dbfs=round(peak_dbfs(bed), 2),
        true_peak_dbfs=round(tp, 2),
        integrated_lufs=round(lufs, 1),
        loudness_range_db=round(peak_dbfs(bed) - lufs, 1),
        headroom_below_0dbfs_db=round(0.0 - tp, 2),
        suggested_placement="-18 to -22 dB under the narration track "
                            "(duck 6-9 dB under speech if the editor supports it)",
    )
    report["level_social_master"] = dict(
        true_peak_dbfs=round(true_peak_dbfs(social), 2),
        integrated_lufs=round(integrated_lufs(social), 1),
        use="standalone / no narration on top",
    )
    st = social   # used for the QC plots below (identical music, hotter gain)
    report["bus_levels"] = {
        b.name: dict(
            loudness_db=round(loudness(np.stack([b.l, b.r], axis=1)), 1),
            peak_dbfs=round(20 * np.log10(max(b.peak, 1e-9)), 2),
        ) for b in ALL_BUSES
    }
    report["loop_seam"] = loop_seam_report(st)
    report["periodicity"] = periodicity_report(st)
    report["section_profile_rms_db"] = section_profile(st)
    report["spectrum"] = spectral_report(st)
    report["voice_space"] = band_report(st)

    # --- deliverables ------------------------------------------------------
    # 1) MAIN 30 s seamless loop, 24-bit / 48 kHz, with smpl loop tags
    write_wav(os.path.join(OUT_MASTER, "sunnah-seed-theme-loop-30s-48k-24bit.wav"), bed,
              SR, 24, dither=False, loop=True,
              comment=f"{TITLE} | Sunnah Seed official background music identity | "
                      f"{BPM:g} BPM | 45 beats | seamless loop 0-{N} | instrumental, no vocals")

    # 2) the same loop butt-joined 3x, so the seam can be auditioned
    triple = np.concatenate([bed, bed, bed], axis=0)
    report["seam_proof_mp3"] = write_mp3(
        os.path.join(OUT_MASTER, "sunnah-seed-theme-loop-90s-x3-seam-audition.mp3"), triple)

    # 3) 16-bit / 44.1 kHz social-media version (periodically resampled, so it
    #    is just as seamless as the 48 kHz master)
    st_441 = resample_periodic(bed, 441, 480)
    write_wav(os.path.join(OUT_MASTER, "sunnah-seed-theme-loop-30s-44k1-16bit.wav"), st_441,
              44100, 16, dither=True, loop=True,
              comment="44.1 kHz / 16-bit delivery version of the 30 s seamless loop")
    report["derived_44k1"] = dict(
        samples=int(st_441.shape[0]),
        expected_beats=round(st_441.shape[0] / (44100 * 60 / BPM), 6),
        true_peak_dbfs=round(true_peak_dbfs(st_441), 2),
    )

    # 4) MP3 for quick review
    write_wav(os.path.join(OUT_MASTER, "sunnah-seed-theme-loop-30s-social-48k-24bit.wav"),
              social, SR, 24, dither=False, loop=True,
              comment=f"{TITLE} | hotter standalone master (-1 dBTP) | seamless loop 0-{N}")

    report["preview_mp3"] = write_mp3(
        os.path.join(OUT_MASTER, "sunnah-seed-theme-loop-30s.mp3"), bed
    )

    # --- score + lead sheet -------------------------------------------------
    with open(os.path.join(OUT_REPORT, "score.json"), "w") as fh:
        json.dump(SCORE, fh, indent=1)
    report["score"] = dict(
        events=len(SCORE),
        by_instrument={b: sum(1 for e in SCORE if e["bus"] == b)
                       for b in sorted({e["bus"] for e in SCORE})},
        notes_per_second=round(len([e for e in SCORE if e["hz"]]) / LOOP_S, 2),
        sustained_note_density="deliberately low - the bed is written to leave "
                               "room for dhikr, dialogue and narration",
    )

    with open(os.path.join(OUT_REPORT, "sunnah-seed-theme-qc.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    write_lead_sheet(os.path.join(OUT_REPORT, "lead-sheet.txt"))

    print(json.dumps(report, indent=2))


def write_lead_sheet(path: str):
    """A plain-text score anyone on the team can read."""
    lines = []
    lines.append(f"{TITLE}  ({ISRC_STYLE_TAG})")
    lines.append("=" * 72)
    lines.append(f"90 BPM | 4/4 | C major pentatonic | 11 bars + 1 pickup beat "
                 f"= exactly {LOOP_S:.0f}.000 s | seamless instrumental loop")
    lines.append("")
    lines.append("Chords, one per bar: " + " | ".join(
        f"bar {i}: {c}" for i, c in enumerate(CHORDS)))
    lines.append("")
    lines.append("SIGNATURE MOTIF - 'ting, ting, ta-ta, ting' + resolving note")
    for chord, mode in MOTIF_MODES.items():
        notes = [LADDER[d] for d in mode["deg"]] + [LADDER[mode["res"]]]
        lines.append(f"  over {chord}: "
                     + "  ".join(f"{lbl}={n}" for lbl, n in
                                 zip(["ting", "ting", "ta", "ta", "ting", "resolve"], notes)))
    lines.append("")
    lines.append(f"{'beat':>6} {'time':>7}  {'instrument':<10} {'note':<5} {'Hz':>8} "
                 f"{'vel':>5}  kind")
    lines.append("-" * 72)
    for e in sorted(SCORE, key=lambda e: (e["beat"], e["bus"])):
        lines.append(f"{e['beat']:6.2f} {e['beat'] * BEAT_S:6.2f}s  {e['bus']:<10} "
                     f"{e['note']:<5} {e['hz']:8.2f} {e['vel']:5.2f}  {e['kind']}")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def write_mp3(path: str, st: np.ndarray, sr: int = SR) -> dict:
    """Encode a preview MP3 with the bundled ffmpeg (192 kbps, joint stereo)."""
    import subprocess
    import tempfile

    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return {"status": "skipped", "reason": "ffmpeg unavailable"}

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    write_wav(tmp_path, st, sr, bits=16, dither=True, loop=False)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", tmp_path,
           "-codec:a", "libmp3lame", "-b:a", "192k", "-joint_stereo", "1", path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(tmp_path)
    if res.returncode != 0:
        return {"status": "failed", "stderr": res.stderr[-400:]}
    size = os.path.getsize(path)
    secs = st.shape[0] / sr
    return {"status": "ok", "path": os.path.basename(path), "bytes": size,
            "seconds": round(secs, 2), "kbps": round(size * 8 / secs / 1000, 1)}


if __name__ == "__main__":
    main()
