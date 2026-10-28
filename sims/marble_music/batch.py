"""Render a week of videos from a plan file and write an upload sheet.

  python3 batch.py weeks/week01.json            # render everything (run overnight)
  python3 batch.py weeks/week01.json --preview  # fast low-res check of the whole batch
  python3 batch.py weeks/week01.json --sheet    # only (re)write the upload sheet

weeks/weekNN.json:
  {"week": 1, "start": "2026-11-02", "time": "17:00",
   "videos": [{"song": "mountain_king", "style": "midnight", "timbre": "glass",
               "hook": "GUESS THE SONG", "seed": 1, "title": "..."}, ...]}

Outputs go to out/weekNN/<nn>-<slug>/final.mp4 plus out/weekNN/UPLOAD.md and
a row per video appended to experiments.csv (the log we join analytics onto).
"""
import csv
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make  # noqa: E402
import song  # noqa: E402

DESC = """{answer_line}Every note is a real bounce: the marble hits a pad exactly on the beat, and each pad plays its own note.
100% original sound, synthesized from scratch. Music: {title} by {composer} (public domain).

#marblemusic #satisfying #asmr #music #{tag}"""

LOG_FIELDS = ["week", "n", "slug", "publish_at", "song", "style", "timbre", "hook", "seed", "title",
              "duration_s", "youtube_id", "views_7d", "avg_view_pct", "swiped_away_pct", "likes_7d",
              "subs_7d", "notes"]


def main(path, preview=False, sheet_only=False):
    wk = json.load(open(path))
    week = int(wk["week"])
    root = os.path.join(HERE, "out", f"week{week:02d}")
    os.makedirs(root, exist_ok=True)
    start = dt.datetime.fromisoformat(f"{wk['start']}T{wk.get('time', '17:00')}")
    rows = []
    for i, v in enumerate(wk["videos"]):
        meta, _, _ = song.load(os.path.join(HERE, "songs", f"{v['song']}.txt"))
        slug = f"{i + 1:02d}-{v['song']}-{v['style']}-{v['timbre']}" + ("-preview" if preview else "")
        when = start + dt.timedelta(days=i)
        if not sheet_only:
            print(f"[{i + 1}/{len(wk['videos'])}] {slug}", flush=True)
            out, info = make.make(v["song"], v["style"], v["timbre"], v.get("hook", ""), v.get("seed", i),
                                  preview, v.get("engine"), out_root=root, slug=slug)
        else:
            info = json.load(open(os.path.join(root, slug, "meta.json")))
        guess = "guess" in v.get("hook", "").lower()
        title = v.get("title") or ("Can you guess this song? 🎵" if guess else f"{meta['title']}, played by a marble 🎵")
        desc = DESC.format(
            answer_line="Answer in the pinned comment 👇\n\n" if guess else "",
            title=meta["title"], composer=meta.get("composer", "Traditional"),
            tag=meta.get("composer", "classical").lower().replace(" ", ""))
        rows.append(dict(week=week, n=i + 1, slug=slug, publish_at=when.isoformat(timespec="minutes"),
                         song=v["song"], style=v["style"], timbre=v["timbre"], hook=v.get("hook", ""),
                         seed=v.get("seed", i), title=title, duration_s=info["duration_s"],
                         answer=f"{meta['title']} by {meta.get('composer', 'Traditional')}", desc=desc))

    with open(os.path.join(root, "UPLOAD.md"), "w") as f:
        f.write(f"# Week {week} upload sheet\n\nFor each video in YouTube Studio: Upload, paste title and description, "
                "Audience: **No, it's not made for kids**, Visibility: **Schedule** at the time below.\n\n")
        for r in rows:
            f.write(f"## {r['n']}. `{r['slug']}/final.mp4`\n\n- **Schedule:** {r['publish_at'].replace('T', ' ')}\n"
                    f"- **Title:** {r['title']}\n- **Pinned comment:** {r['answer']} 🎹 Did you get it?\n\n"
                    f"```\n{r['desc']}\n```\n\n")

    if not preview and not sheet_only:
        log = os.path.join(HERE, "experiments.csv")
        new = not os.path.exists(log)
        with open(log, "a", newline="") as f:
            w = csv.DictWriter(f, LOG_FIELDS, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerows(rows)
    print(f"upload sheet: {root}/UPLOAD.md")


if __name__ == "__main__":
    main(sys.argv[1], "--preview" in sys.argv, "--sheet" in sys.argv)
