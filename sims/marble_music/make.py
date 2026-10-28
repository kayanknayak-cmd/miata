"""One video, start to finish.

  python3 make.py --song fur_elise --style candy --timbre marimba --hook "GUESS THE SONG"
  python3 make.py --song mountain_king --style midnight --timbre glass --preview

Writes out/<slug>/: plan.json, style.json, audio.wav, silent.mp4, final.mp4, meta.json
Blender is found via $BLENDER, the default macOS app path, or `blender` on PATH.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio  # noqa: E402
import plan as planner  # noqa: E402
import song  # noqa: E402

MAC_BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"


def find_blender():
    for c in (os.environ.get("BLENDER"), MAC_BLENDER, shutil.which("blender")):
        if c and os.path.exists(c):
            return c
    sys.exit("Blender not found: set BLENDER=/path/to/blender")


def make(song_id, style_id, timbre, hook="", seed=0, preview=False, engine=None, out_root=None, slug=None):
    meta, events, length = song.load(os.path.join(HERE, "songs", f"{song_id}.txt"))
    slug = slug or f"{song_id}-{style_id}-{timbre}-s{seed}" + ("-preview" if preview else "")
    out = os.path.join(out_root or os.path.join(HERE, "out"), slug)
    os.makedirs(out, exist_ok=True)

    style = json.load(open(os.path.join(HERE, "styles", f"{style_id}.json")))
    style["hook"] = hook
    if engine:
        style["engine"] = engine
    pl = planner.best(events, length, style.get("plan", {}), seed=seed)
    json.dump(pl, open(f"{out}/plan.json", "w"))
    json.dump(style, open(f"{out}/style.json", "w"), indent=1)

    audio.render(pl, timbre, f"{out}/audio.wav", seed=seed)

    cmd = [find_blender(), "-b", "-P", os.path.join(HERE, "blender_scene.py"), "--",
           f"{out}/plan.json", f"{out}/style.json", f"{out}/silent.mp4"] + (["--preview"] if preview else [])
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{out}/silent.mp4", "-i", f"{out}/audio.wav",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
                    f"{out}/final.mp4"], check=True)

    info = {
        "slug": slug, "song": song_id, "title_song": meta.get("title"), "composer": meta.get("composer"),
        "style": style_id, "timbre": timbre, "hook": hook, "seed": seed,
        "duration_s": round(pl["duration"], 1), "hits": len(pl["pads"]),
    }
    json.dump(info, open(f"{out}/meta.json", "w"), indent=1)
    return out, info


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True)
    ap.add_argument("--style", default="candy")
    ap.add_argument("--timbre", default="marimba", choices=sorted(audio.TIMBRES))
    ap.add_argument("--hook", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--engine", choices=["eevee", "cycles"])
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    out, info = make(a.song, a.style, a.timbre, a.hook, a.seed, a.preview, a.engine)
    print(f"done: {out}/final.mp4 ({info['duration_s']}s, {info['hits']} hits)")
