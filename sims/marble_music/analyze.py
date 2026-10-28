"""Weekly read-out from experiments.csv (filled in from YouTube Studio screenshots).

  python3 analyze.py            # all weeks
  python3 analyze.py --week 1

For each factor (song, style, timbre, hook) prints the median 7-day views, viewed-vs-swiped
and average % viewed. With 7 videos a week this is directional, not statistically solid:
act on big gaps (2x or more), and re-test before trusting small ones.
"""
import csv
import os
import statistics as st
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def num(x):
    try:
        return float(str(x).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def main(week=None):
    rows = list(csv.DictReader(open(os.path.join(HERE, "experiments.csv"))))
    rows = [r for r in rows if num(r["views_7d"]) is not None and (week is None or int(r["week"]) == week)]
    if not rows:
        sys.exit("no rows with views_7d yet")
    print(f"{len(rows)} videos with 7-day data\n")
    print("Top videos:")
    for r in sorted(rows, key=lambda r: -num(r["views_7d"]))[:10]:
        sw, avp = num(r["swiped_away_pct"]), num(r["avg_view_pct"])
        print(f"  {num(r['views_7d']):>10,.0f}  viewed {'?' if sw is None else f'{100 - sw:.0f}':>3}%"
              f"  avg {'?' if avp is None else f'{avp:.0f}':>3}%  {r['slug']}")
    for factor in ("song", "style", "timbre", "hook"):
        g = defaultdict(list)
        for r in rows:
            g[r[factor] or "(none)"].append(r)
        if len(g) < 2:
            continue
        print(f"\nby {factor}:")
        for k, rs in sorted(g.items(), key=lambda kv: -st.median(num(r["views_7d"]) for r in kv[1])):
            v = st.median(num(r["views_7d"]) for r in rs)
            avp = [num(r["avg_view_pct"]) for r in rs if num(r["avg_view_pct"]) is not None]
            print(f"  {k:16} n={len(rs):2}  median views {v:>10,.0f}" +
                  (f"  avg viewed {st.mean(avp):5.1f}%" if avp else ""))


if __name__ == "__main__":
    main(int(sys.argv[sys.argv.index("--week") + 1]) if "--week" in sys.argv else None)
