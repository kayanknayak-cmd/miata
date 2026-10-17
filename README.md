# Miata flipbook edit

30s, 12fps, 1920x1080. NA -> NB -> NC -> ND; pencil flipbook turns into colour film around the NC.

- `tools/fetch.py OUT N` pulls CC photos per generation from Wikimedia Commons (rate limited; rerun if a generation comes back empty).
- `tools/render.py SCRATCH [frames]` renders `SCRATCH/frames/*.png` (144 BPM = 5 frames per beat; zoom punch on beats, flash on bars).
- `tools/beat.py out.wav 30` placeholder synth beat.
- `out/CREDITS.tsv` photo attribution (required by CC BY / BY-SA; include in your contest post).

Assemble:
`ffmpeg -framerate 12 -i frames/%04d.png -i beat.wav -c:v libx264 -tune grain -crf 24 -pix_fmt yuv420p -c:a aac -t 30 out.mp4`
