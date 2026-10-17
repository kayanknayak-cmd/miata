# Miata flipbook edit (v3)

`out/miata_v3.mp4`: 30.0s, 12fps, 1080x1920 vertical. Cut-out Miatas locked centre-frame, a different car every frame (sorted by paint colour), NA -> NB -> NC -> ND; retro sun background and film look swap on the beat. Ends on a red ND hero.
Shots rotate on the beat: drive-in with motion blur, locked flipbook with spinning sunburst and push-in, headlight/wheel close-ups, drive-by with scrolling pillars, 3x3 grid pop-in; whip-pan flash into each generation; title slam.

Music: "Disco Medusae" by Kevin MacLeod (incompetech.com), CC BY 4.0, 1:13.6 to 1:43.6.
Photo attribution: `out/CREDITS.tsv` (CC BY / BY-SA requires credit in your post).

Pipeline: `fetch2.py` (Wikimedia Commons) -> `cutout.py` (rembg + quality filter) -> `sheet.py` (eyeball check) -> `render3.py` -> ffmpeg (see commit history for flags).
