"""Parse song text files into hit events: [(time_s, [midi pitches])]."""
import re

DUR = {"w": 4.0, "h": 2.0, "q": 1.0, "e": 0.5, "s": 0.25, "t": 0.125}
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def dur_beats(tok):
    base = DUR[tok[0]]
    return base * 1.5 if tok.endswith(".") else base


def midi(name):
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", name)
    if not m:
        raise ValueError(f"bad note {name!r}")
    n = NOTE[m[1]] + {"#": 1, "b": -1, "": 0}[m[2]]
    return 12 * (int(m[3]) + 1) + n


def load(path):
    meta, toks, in_notes = {}, [], False
    for line in open(path, encoding="utf-8"):
        line = "" if line.lstrip().startswith("#") else line.strip()  # '#' is also a sharp
        if not line:
            continue
        if in_notes:
            toks += line.split()
        elif line == "notes:":
            in_notes = True
        else:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    # bpm "120" or "120 -> 260" (linear ramp in tempo across the piece, measured in beats)
    bpm = [float(x) for x in meta.get("bpm", "120").split("->")]
    bpm0, bpm1 = bpm[0], bpm[-1]
    beat = dur_beats(meta.get("beat", "q"))  # the unit bpm counts, in quarter notes

    toks = toks * int(meta.get("repeat", 1))
    items = []  # (start_quarters, dur_quarters, pitches)
    pos = 0.0
    for tok in toks:
        pitch, d = tok.split("/")
        q = dur_beats(d)
        if pitch != "r":
            items.append((pos, q, [midi(p) for p in pitch.split("+")]))
        pos += q
    total = pos

    # integrate time with a tempo that ramps linearly with position
    def t_at(qpos, steps=400):
        t, dq = 0.0, qpos / steps if steps else 0
        for i in range(steps):
            frac = (i + 0.5) * dq / total if total else 0
            b = bpm0 + (bpm1 - bpm0) * frac
            t += dq / beat * 60.0 / b
        return t

    events = [(t_at(p), ps) for p, _, ps in items]
    return meta, events, t_at(total)


if __name__ == "__main__":
    import sys
    meta, ev, length = load(sys.argv[1])
    print(meta.get("title"), f"{len(ev)} hits, {length:.1f}s")
    for t, ps in ev[:10]:
        print(f"{t:6.3f} {ps}")
