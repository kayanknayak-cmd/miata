"""Quick 2D sanity plot of a plan (pads + ball path). Not part of the final render."""
import sys
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import plan as P


def draw(pl, out):
    ts = np.linspace(0, pl["duration"], 3000)
    xy = np.array([P.ball_at(pl, t) for t in ts])
    ymin = min(p["pos"][1] for p in pl["pads"]) - 1
    h = xy[:, 1].max() - ymin
    fig, ax = plt.subplots(figsize=(4, max(4, h * 0.9)))
    ax.plot(xy[:, 0], xy[:, 1], lw=0.6, color="#888")
    for p in pl["pads"]:
        a, b = P.pad_ends(p)
        ax.plot([a[0], b[0]], [a[1], b[1]], lw=3, color=plt.cm.hsv((p["pitches"][0] % 12) / 12), solid_capstyle="round")
    ax.set_aspect("equal"); ax.set_xlim(-2, 2); ax.set_ylim(ymin, xy[:, 1].max() + 0.2)
    fig.savefig(out, dpi=80, bbox_inches="tight")


if __name__ == "__main__":
    draw(json.load(open(sys.argv[1])), sys.argv[2])
