# Sunnah Seed Theme — “Morning Seeds”

**The official recurring background-music identity for Sunnah Seed.**

A 30-second, seamlessly looping, purely instrumental piece for Muslim toddlers aged 1–4.
Warm wooden mallets, a soft preschool bounce, and one short motif that children can learn to
recognise — so that after a few videos the sound alone says *“Sunnah Seed”*.

| | |
|---|---|
| **Catalogue tag** | `SS-THEME-001` |
| **Tempo** | 90 BPM |
| **Length** | 30.000 s exactly — 45 beats, 11 bars of 4/4 + one pickup beat |
| **Key** | C major pentatonic |
| **Content** | Instrumental only. No vocals, lyrics, recitation, chanting or humming. |
| **Master** | −22.3 LUFS integrated · −5.94 dBTP true peak |
| **Loop** | Circular by construction — no fade, no crossfade, no gap |

---

## Listen first

```bash
python tools/audio/sunnah_seed/preview_server.py 8080
# then open http://localhost:8080/
```

The preview page plays the loop with sample-accurate scheduling (one buffer per pass on the audio
clock), so what you hear is genuinely gapless — the same thing you get in an edit.

Quick audition without the server: `master/sunnah-seed-theme-loop-30s.mp3`
Hunt for the seam: `master/sunnah-seed-theme-loop-90s-x3-seam-audition.mp3` — three passes back to back.

---

## Files

```
assets/audio/sunnah-seed/
├── master/
│   ├── sunnah-seed-theme-loop-30s-48k-24bit.wav        ← THE master loop (use this)
│   ├── sunnah-seed-theme-loop-30s-44k1-16bit.wav       ← social / mobile delivery
│   ├── sunnah-seed-theme-loop-30s-social-48k-24bit.wav ← hotter, for pieces with no narration
│   ├── sunnah-seed-theme-loop-30s.mp3                  ← 192 kbps preview
│   └── sunnah-seed-theme-loop-90s-x3-seam-audition.mp3 ← seam test
├── stems/         8 mix-ready layers, 16-bit/48 kHz (regenerable — see below)
├── spec/
│   ├── sunnah-seed-theme-qc.json   objective measurements of the master
│   ├── score.json                  every scheduled event
│   └── lead-sheet.txt              the same score, human-readable
└── index.html     the interactive player
```

The three `.wav` masters carry a RIFF `smpl` loop chunk plus a cue point, so Reaper, Premiere,
Resolve, Audition, Logic and Audacity can loop the file bar-perfectly without any trimming.

---

## How to use it in a video

1. Drop `sunnah-seed-theme-loop-30s-48k-24bit.wav` on a music track and **loop it end to end**.
   Do not add fades and do not trim — the file is one exact period of the music.
2. Set the music roughly **18–22 dB under the narration track**, or about −30 to −28 LUFS in the
   final mix. If your editor has ducking, 6–9 dB under speech is plenty.
3. Record dhikr, child dialogue and parent dialogue on top. The bed leaves the 100 Hz–4 kHz band
   deliberately open for voices, and there is no content at all below 28 Hz or above 16 kHz.
4. For a Reel, Short or TikTok, the loop length means 2 passes = 60 s, 4 passes = 120 s — always
   landing on a full bar.
5. If you need it louder and nothing is spoken over it, use the `social` master instead.

For a quieter moment (a soft scene, a salah segment), pull the **percussion**, **frame_drum** and
**chime** stems out of `stems/` and you get the same music with the toys taken away.

---

## The music

**Signature motif — “ting · ting · ta-ta · ting” + a soft resolving note**

```
 beat:    0      1      2     2½     3      3½
         ting   ting   ta-   -ta   ting  (resolve)
 over C:  E5     G5     A5    G5    E5     G5
 over G:  D5     G5     A5    G5    D5     G5
 over F:  C5     D5     E5    D5    C5     E5
```

The rhythm never changes; only the pitches move to sit on each chord. That is what makes it stick
while staying fresh. It is stated five times in the 30 seconds, on kalimba, marimba and xylophone.

**Form** (measured from the rendered master, not just intended):

| Time | Section | What happens | RMS |
|---|---|---|---|
| 0–5 s | Soft opening | kalimba motif alone, pad and wooden bass | −22.4 dB |
| 5–10 s | Marimba enters | subtle marimba, first tiny bell | −20.7 dB |
| 10–20 s | **Main identity** | full palette, claps on 2 and 4, full motif | −18.6 dB |
| 20–25 s | Breathing space | drum and claps drop out, two soft tines only | −20.7 dB |
| 25–30 s | Return | back to the opening gesture, into the pickup | −22.6 dB |

**Harmony** — one chord per bar: `C · G · F · C · C · G · F · C · F · G · C`.
The last bar is C, which is also the first bar, so the loop point is harmonically stable.
Verified against the audio with a beat-synchronous chromagram: all 11 bars match.

**Instrumentation**, and how loud each layer actually is in the mix:

| Layer | Loudness | Peak |
|---|---|---|
| kalimba (lead voice) | −28.0 dB | −14.7 dBFS |
| marimba (second voice) | −29.5 dB | −16.0 dBFS |
| airy warm pad | −34.8 dB | −23.3 dBFS |
| soft wooden bass | −35.5 dB | −22.1 dBFS |
| tiny chime accents | −36.0 dB | −19.7 dBFS |
| wooden xylophone | −37.0 dB | −16.6 dBFS |
| light hand percussion | −38.0 dB | −12.3 dBFS |
| very subtle frame drum | −38.5 dB | −10.9 dBFS |

Nothing is aggressive, nothing is electronic, there is no heavy bass, no EDM, no trap, no cinematic
orchestra and no loud synthesizers. The spectral centroid is 733 Hz; 82 % of the energy sits in the
warm 250 Hz–2 kHz band.

---

## Why the loop is genuinely seamless

This is not a crossfade or a clever edit — it is a mathematical property of how the track was made.

* The whole track is rendered into a ring buffer of **exactly** 1 440 000 samples.
* 90 BPM at 48 kHz means one beat is **exactly 32 000 samples**, so bar lines never land mid-sample.
* Every note tail is added with wrap-around, so a note that starts near the end finishes
  at the beginning — as it should.
* Reverb is a **circular** convolution, so the tail of the last note is already present in the
  first moments of the file. Nothing is truncated.
* The pad oscillators are tuned to exact integer multiples of 1/30 Hz, so they complete a whole
  number of cycles per loop and are perfectly periodic.
* EQ and the (unused) limiter are applied with circular filtering, so no filter state leaks
  across the loop point.
* Even the 44.1 kHz version is resampled with wrap-around, and 16-bit dither is periodic, so the
  derived files loop just as cleanly.

Measured on the master:

| Check | Result |
|---|---|
| Seam discontinuity vs. loudest step in the file | −32.5 dBFS vs −8.3 dBFS |
| High-frequency burst score at the seam | −0.14 σ (i.e. an ordinary sample) |
| Compared with the *other* bar lines inside the track | the loop point is **less** active than they are |
| Limiter gain reduction | 0.00 dB — nothing needed squashing |
| Filter repeatability across the loop point | 0.000000000000 |

Objectively, the loop point is indistinguishable from any ordinary bar line. Practically: loop it
four times and you will not find where one pass ends.

---

## Regenerating / editing the music

The whole track is **code**, deterministically seeded — reruns are bit-identical.

```bash
python -m venv .venv && .venv/bin/pip install numpy scipy imageio-ffmpeg

cd tools/audio/sunnah_seed
.venv/bin/python compose.py     # ~16 s: renders masters, stems, score and QC report
.venv/bin/python verify.py      # checks the audio back against the score
```

| File | What it holds |
|---|---|
| `synth.py` | the instruments (modal mallets, frame drum, percussion, pad, circular reverb) and the loop-safe WAV writer |
| `compose.py` | the score, the arrangement, the mix, the mastering and the QC measurements |
| `verify.py` | independent read-back checks: onsets, pitches, motif, harmony, density |
| `preview_server.py` | the audition server |

Want a different tempo, key, or a calm version without percussion? Change `BPM`, the `LADDER`
and `CHORDS` at the top of `compose.py`, or mute a bus in `BALANCE`. Everything downstream —
loop points, stems, QC report, lead sheet — follows automatically.

`stems/` is excluded from git because it is regenerable in seconds; run `compose.py` to rebuild it.

---

## Verify it yourself

```bash
.venv/bin/python tools/audio/sunnah_seed/verify.py
```

It reads the rendered stems back off disk and confirms: the motif comes out as
`E5 G5 A5 G5 E5 G5` over C and `C5 D5 E5 D5 C5 E5` over F, every bar's chroma matches the scored
chord, and the density follows the five-section form. It is not listening to itself — it analyses
the audio files.

---

## Scope note

This is a background music bed only. No religious text is sung, spoken or implied, so the same
30 seconds can sit under a Bismillah lesson, an Alhamdulillah lesson, a tooth-brushing Sunnah or a
bedtime du'a without ever being “the wrong track”. The dhikr and dialogue are recorded separately
during video production.
