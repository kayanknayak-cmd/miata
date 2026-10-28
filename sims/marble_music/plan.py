"""Turn hit events into a physically plausible bounce path.

The ball flies on ballistic arcs (gravity only) and hits one pad per note onset,
exactly on time. Each pad is tilted so the bounce is a mirror reflection of the
incoming velocity. Pads are placed by a small search that rejects layouts where
the ball would clip another pad or a pad would sit on the ball's earlier path.

Output: plan dict (JSON-serialisable) consumed by audio.py and blender_scene.py.
"""
import math
import random

import numpy as np


def _traj(p0, v0, g, t):
    """Positions along a ballistic arc at times t (array) after launch."""
    t = np.asarray(t)[:, None]
    return p0[None, :] + v0[None, :] * t + 0.5 * np.array([0.0, -g])[None, :] * t * t


def _seg_dist(pts, a, b):
    """Distance from each point in pts to segment a-b."""
    ab = b - a
    L2 = float(ab @ ab) or 1e-9
    u = np.clip(((pts - a) @ ab) / L2, 0, 1)
    return np.linalg.norm(pts - (a + u[:, None] * ab), axis=1)


def pad_ends(pad):
    c, tang, w = np.array(pad["pos"]), np.array(pad["tangent"]), pad["width"]
    return c - tang * w / 2, c + tang * w / 2


def build(events, length, cfg, seed=0):
    rng = random.Random(seed)
    g = cfg.get("gravity", 22.0)
    r_ball = cfg.get("ball_radius", 0.15)
    half_w = cfg.get("half_width", 1.25)  # keep pads inside the 9:16 frame
    thick = cfg.get("pad_thickness", 0.1)
    lead = cfg.get("lead_in", 0.9)
    clear = r_ball + thick / 2 + 0.03

    times = [lead + t for t, _ in events]
    pads, samples = [], []  # samples: past ball centres (for keep-out checks)
    # first hit: dropped from rest, straight down onto pad 0 at the origin
    p = np.array([0.0, 0.0])
    v_in = np.array([0.0, -g * times[0]])
    start = p - np.array([0.0, -0.5 * g * times[0] ** 2])  # where the ball starts
    segs = [{"t0": 0.0, "t1": times[0], "p0": start.tolist(), "v0": [0.0, 0.0]}]
    samples.append(_traj(start, np.zeros(2), g, np.linspace(0, times[0], 40)))
    direction = rng.choice([-1, 1])
    # per-seed "personality" so the same song never lays out the same way twice
    k_dx = cfg.get("spread", rng.uniform(0.8, 1.25))
    k_dy = cfg.get("steepness", rng.uniform(0.8, 1.3))
    p_switch = cfg.get("switchback", rng.uniform(0.05, 0.3))

    for i, (t, (_, pitches)) in enumerate(zip(times, events)):
        last = i == len(times) - 1
        dt = (times[i + 1] - t) if not last else 0.6
        best = None
        # candidate next-hit offsets, tried in order of preference
        base_dx = k_dx * max(0.38, min(1.1, 0.55 + 0.9 * dt)) * rng.uniform(0.9, 1.1)
        base_dy = k_dy * (0.18 + 1.1 * dt) * rng.uniform(0.9, 1.1)
        cands = []
        for flip in (False, True):
            d = -direction if flip else direction
            for sx in (1.0, 1.3, 0.8, 1.7, 0.6, 2.1):
                for sy in (1.0, 1.4, 2.0, 0.6, 2.8, 0.4, 4.0):
                    cands.append((d, sx, sy))
        if rng.random() < p_switch and dt > 0.2:  # occasional switch-back for variety
            cands.sort(key=lambda c: c[0] == direction)
        for d, sx, sy in cands:
            dx, dy = d * base_dx * sx, -base_dy * sy
            q = p + np.array([dx, dy])
            if abs(q[0]) > half_w:
                continue
            v_out = np.array([dx / dt, (dy + 0.5 * g * dt * dt) / dt])
            n = v_out / np.linalg.norm(v_out) - v_in / np.linalg.norm(v_in)
            if np.linalg.norm(n) < 1e-6:
                continue
            n /= np.linalg.norm(n)
            if n[1] < 0.25:  # pad would face sideways/down: looks wrong
                continue
            width = max(0.34, min(0.75, 0.3 + 0.8 * min(dt, 0.6)))
            tang = np.array([n[1], -n[0]])
            centre = p - n * (r_ball + thick / 2)
            pad = {"pos": centre.tolist(), "normal": n.tolist(), "tangent": tang.tolist(), "width": width}
            a, b = pad_ends(pad)
            # 1) this pad must not sit on the ball's earlier path (its own approach arc is exempt)
            past = np.concatenate(samples[:-1]) if len(samples) > 1 else np.zeros((0, 2))
            if len(past) and _seg_dist(past, a, b).min() < clear:
                continue
            # 2) the outgoing arc must clear every existing pad (except where it lands next)
            arc = _traj(p, v_out, g, np.linspace(0.04, dt - 0.04, 36)) if not last else None
            ok = True
            if arc is not None:
                for op in pads:
                    oa, ob = pad_ends(op)
                    if _seg_dist(arc, oa, ob).min() < clear:
                        ok = False
                        break
                # the arc must not pass back through the pad it leaves from
                if ok and _seg_dist(arc, a, b).min() < r_ball + thick / 2 - 0.01:
                    ok = False
            # 3) pads must not overlap each other
            if ok:
                for op in pads[-40:]:
                    if np.linalg.norm(np.array(op["pos"]) - centre) < (op["width"] + width) / 2 * 0.9 and \
                       abs(np.array(op["pos"])[1] - centre[1]) < 0.25:
                        ok = False
                        break
            if not ok:
                continue
            best = (d, q, v_out, pad, arc)
            break
        if best is None:
            # fallback: big drop straight below, always feasible enough
            d = -direction
            dx, dy = d * base_dx, -(base_dy * 6 + 1.0)
            q = p + np.array([dx, dy])
            v_out = np.array([dx / dt, (dy + 0.5 * g * dt * dt) / dt])
            n = v_out / np.linalg.norm(v_out) - v_in / np.linalg.norm(v_in)
            n /= np.linalg.norm(n)
            tang = np.array([n[1], -n[0]])
            pad = {"pos": (p - n * (r_ball + thick / 2)).tolist(), "normal": n.tolist(), "tangent": tang.tolist(),
                   "width": 0.4, "fallback": True}
            best = (d, q, v_out, pad, _traj(p, v_out, g, np.linspace(0.04, dt - 0.04, 36)))
        direction, q, v_out, pad, arc = best
        pad.update({"time": t, "pitches": pitches, "speed": float(np.linalg.norm(v_in)), "hit": p.tolist()})
        pads.append(pad)
        segs.append({"t0": t, "t1": t + dt, "p0": p.tolist(), "v0": v_out.tolist()})
        if arc is not None:
            samples.append(arc)
        v_in = v_out + np.array([0.0, -g * dt])
        p = q

    # tail: last bounce flies off and falls away
    end = times[-1] + cfg.get("tail", 2.2)
    segs[-1]["t1"] = end
    return {
        "gravity": g, "ball_radius": r_ball, "pad_thickness": thick, "lead_in": lead,
        "duration": end, "pads": pads, "segments": segs,
    }


def best(events, length, cfg, seed=0, tries=8):
    """Build several layouts from one seed and keep the one with fewest emergency drops."""
    plans = [build(events, length, cfg, seed=seed * 1000 + k) for k in range(tries)]
    for pl in plans:
        pl["fallbacks"] = sum(1 for p in pl["pads"] if p.get("fallback"))
    return min(plans, key=lambda pl: pl["fallbacks"])


def ball_at(plan, t):
    g = plan["gravity"]
    for s in plan["segments"]:
        if s["t0"] <= t <= s["t1"] or s is plan["segments"][-1]:
            dt = t - s["t0"]
            return (s["p0"][0] + s["v0"][0] * dt, s["p0"][1] + s["v0"][1] * dt - 0.5 * g * dt * dt)


if __name__ == "__main__":
    import json
    import sys

    import song

    meta, ev, length = song.load(sys.argv[1])
    pl = best(ev, length, {}, seed=1)
    ys = [p["pos"][1] for p in pl["pads"]]
    print(f"{len(pl['pads'])} pads, drop {ys[0] - ys[-1]:.1f} units, x range "
          f"{min(p['pos'][0] for p in pl['pads']):.2f}..{max(p['pos'][0] for p in pl['pads']):.2f}")
    json.dump(pl, open("/tmp/plan.json", "w"))
