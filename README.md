# Miata flipbook edit (v2)

`out/miata_v2.mp4`: 30.0s, 12fps, 1080x1920 vertical. Cut-out Miatas locked centre-frame, a different car every frame (sorted by paint colour), NA -> NB -> NC -> ND; retro sun background and film look swap on the beat. Ends on a red ND hero.

Music: "Disco Medusae" by Kevin MacLeod (incompetech.com), CC BY 4.0, 1:13.6 to 1:43.6.
Photo attribution: `out/CREDITS.tsv` (CC BY / BY-SA requires credit in your post).

Pipeline: `fetch2.py` (Wikimedia Commons) -> `cutout.py` (rembg + quality filter) -> `sheet.py` (eyeball check) -> `render2.py` -> ffmpeg (see commit history for flags).
