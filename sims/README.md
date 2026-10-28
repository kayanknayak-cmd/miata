# Marble music Shorts

The system for a daily Shorts channel. A marble bounces down a set of pads, and every bounce plays one note
of a public-domain melody. The audio is synthesized from scratch, so it's original and claim-free.

- `research/`: the data behind the format choice (4,883 Shorts scraped, see `research/FINDINGS.md`)
- `marble_music/`: the pipeline

## Pipeline

```
songs/*.txt ─▶ song.py ─▶ plan.py ─────▶ audio.py ──────────▶ audio.wav ─┐
 (melody)      (events)   (pad layout,    (struck-bar synthesis,          ├─ ffmpeg ─▶ final.mp4
                           exact-timing    marble tick, pan, reverb,      │
                           bounces)        -14 LUFS)                      │
                              └──────────▶ blender_scene.py ─▶ silent.mp4 ┘
                                           (pads, ball, camera, glow, hook text)
```

## Setup (Mac, once)

```
brew install ffmpeg python
pip3 install numpy scipy pyloudnorm
```
Blender 4.2 or newer in /Applications (or set `BLENDER=/path/to/blender`).

## Make videos

```
cd sims/marble_music
python3 make.py --song mountain_king --style midnight --timbre glass --hook "GUESS THE SONG" --preview  # ~1 min check
python3 batch.py weeks/week01.json --preview   # low-res check of the whole week
python3 batch.py weeks/week01.json             # full 1080x1920 60fps render, run overnight
```
Output goes to `out/week01/NN-.../final.mp4`, and `out/week01/UPLOAD.md` holds the title, description,
pinned comment and schedule time for each video.

- **Songs:** `fur_elise`, `mountain_king`, `ode_to_joy`, `korobeiniki` (own transcriptions, so check each by ear in a preview)
- **Styles:** `candy`, `midnight`, `mint`, `lilac` (`styles/*.json`)
- **Timbres:** `marimba`, `glass`, `musicbox`, `vibes`, `kalimba`, `steelpan`

Adding a song: copy a file in `songs/`, keep to public-domain compositions, and write the notes yourself.
Downloaded MIDI arrangements can carry their own copyright.

## Weekly loop

1. Run `batch.py` and schedule all 7 videos in YouTube Studio from `UPLOAD.md`.
2. After 7 days, screenshot YouTube Studio > Analytics > Content > Shorts (views, viewed vs swiped away,
   average % viewed, subscribers) and each video's row.
3. Hand the screenshots to Claude, which fills `experiments.csv` and writes next week's `weeks/weekNN.json`,
   doubling down on what worked.
