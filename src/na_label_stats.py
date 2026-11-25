#!/usr/bin/env python3
"""Net force of the Na reference labels per config_type: transition states vs equilibrium.

Usage: python3 src/na_label_stats.py DATASET_DIR --sums SUMS --out DIR
DATASET_DIR: the consolidado/ dir (read-only). Reads train.xyz and valid.xyz only (training
side; test.xyz is never opened) and checks both against the sha256 list SUMS
(data/consolidado.sha256). Writes DIR/frames.tsv (one row per frame), DIR/by_config_type.tsv
and DIR/verdict.json, and prints the reading.

Per frame: |SF| = norm of the summed REF_forces (eV/A; zero for exact forces in a periodic
cell, so it measures label error) and, for frames with Na, x = |SF| / sqrt(n_Na).

Reading (fixed before the run; owner "faz a checagem", 2026-11-25; the medians of |SF| per
config_type were already known, the tails were not):
- TS = frames of interface_W4aTS, interface_W4aTSr, interface_W4bTS, interface_W4bTSr pooled;
  EQ = frames of interface_aimd, interface_longa pooled. r_p90 = p90(x, TS) / p90(x, EQ),
  r_max = max(x, TS) / max(x, EQ).
- "same" if 0.8 <= r_p90 <= 1.25 and 0.8 <= r_max <= 1.25; "TS worse" if r_p90 > 1.5 and
  r_max > 1.5; otherwise "inconclusive".
- Reported only: r_median; the restrained windows (interface_N3, interface_W4a,
  interface_W4b) vs EQ; n, median, p90 and max per config_type (x for Na types, |SF| for
  Na-free types).
Percentiles: linear interpolation between order statistics (numpy's default).
Standard library only; runs on Python >= 3.6.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

SPLITS = ("train", "valid")
TS = ("interface_W4aTS", "interface_W4aTSr", "interface_W4bTS", "interface_W4bTSr")
EQ = ("interface_aimd", "interface_longa")
WINDOWS = ("interface_N3", "interface_W4a", "interface_W4b")
SAME = (0.8, 1.25)
WORSE = 1.5
KV_RE = re.compile(r'(\w+)=("([^"]*)"|\S+)')


def sha256(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_sums(dataset, sums_text):
    want = {}
    for line in sums_text.splitlines():
        t = line.split()
        if len(t) == 2:
            want[Path(t[1]).name] = t[0]
    for s in SPLITS:
        name = s + ".xyz"
        if want.get(name) != sha256(dataset / name):
            raise ValueError("{}: sha256 missing from the list or different".format(name))


def parse_header(line):
    kv = {m.group(1): (m.group(3) if m.group(3) is not None else m.group(2))
          for m in KV_RE.finditer(line)}
    cols, i = {}, 0
    t = kv["Properties"].split(":")
    for name, n in zip(t[0::3], t[2::3]):
        cols[name] = (i, i + int(n))
        i += int(n)
    return kv, cols


def read_frames(text, split):
    """extxyz text -> [{"config_type", "split", "n_atoms", "n_na", "sumF"}]."""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        n = int(lines[i])
        kv, cols = parse_header(lines[i + 1])
        sp, (f0, f1) = cols["species"][0], cols["REF_forces"]
        tot, n_na = [0.0, 0.0, 0.0], 0
        for a in lines[i + 2:i + 2 + n]:
            t = a.split()
            n_na += t[sp] == "Na"
            for c, v in enumerate(t[f0:f1]):
                tot[c] += float(v)
        out.append({"config_type": kv["config_type"], "split": split, "n_atoms": n,
                    "n_na": n_na, "sumF": math.sqrt(sum(v * v for v in tot))})
        i += 2 + n
    return out


def percentile(vals, q):
    s = sorted(vals)
    if not s:
        raise ValueError("empty sample")
    pos = (len(s) - 1) * q / 100.0
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def stats(vals):
    return {"n": len(vals), "median": percentile(vals, 50), "p90": percentile(vals, 90),
            "max": max(vals)}


def x_of(frames, types):
    return [f["sumF"] / math.sqrt(f["n_na"]) for f in frames
            if f["config_type"] in types and f["n_na"] > 0]


def reading(frames):
    ts, eq = stats(x_of(frames, TS)), stats(x_of(frames, EQ))
    win = stats(x_of(frames, WINDOWS))
    r = {k: ts[k] / eq[k] for k in ("median", "p90", "max")}
    if all(SAME[0] <= r[k] <= SAME[1] for k in ("p90", "max")):
        verdict = "same"
    elif all(r[k] > WORSE for k in ("p90", "max")):
        verdict = "TS worse"
    else:
        verdict = "inconclusive"
    return {"verdict": verdict, "r_p90": r["p90"], "r_max": r["max"], "r_median": r["median"],
            "TS": ts, "EQ": eq, "windows": win,
            "windows_over_EQ": {k: win[k] / eq[k] for k in ("median", "p90", "max")}}


def commit_of(repo):
    try:
        head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"])
        dirty = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"])
        return head.decode().strip(), bool(dirty.strip())
    except (OSError, subprocess.CalledProcessError):
        return "unknown", None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dataset")
    ap.add_argument("--sums", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    dataset, out = Path(a.dataset), Path(a.out)
    check_sums(dataset, Path(a.sums).read_text())
    frames = []
    for s in SPLITS:
        frames += read_frames((dataset / (s + ".xyz")).read_text(), s)
    r = reading(frames)
    by_type = {}
    for f in frames:
        by_type.setdefault(f["config_type"], []).append(f)
    out.mkdir(parents=True, exist_ok=True)
    rows = ["config_type\tn_na\tquantity\tn\tmedian\tp90\tmax"]
    for ct, fs in sorted(by_type.items()):
        na = fs[0]["n_na"]
        vals = x_of(fs, (ct,)) if na else [f["sumF"] for f in fs]
        st = stats(vals)
        rows.append("\t".join([ct, str(na), "|SF|/sqrt(n_Na)" if na else "|SF|", str(st["n"])]
                              + ["{:.3f}".format(st[k]) for k in ("median", "p90", "max")]))
    (out / "by_config_type.tsv").write_text("\n".join(rows) + "\n")
    fr = ["config_type\tsplit\tn_atoms\tn_na\tsumF_eV_A"]
    fr += ["\t".join([f["config_type"], f["split"], str(f["n_atoms"]), str(f["n_na"]),
                      "{:.6f}".format(f["sumF"])]) for f in frames]
    (out / "frames.tsv").write_text("\n".join(fr) + "\n")
    commit, dirty = commit_of(Path(__file__).resolve().parent.parent)
    (out / "verdict.json").write_text(json.dumps(
        {"commit": commit, "dirty": dirty, "dataset": str(dataset.resolve()),
         "sha256": {s + ".xyz": sha256(dataset / (s + ".xyz")) for s in SPLITS},
         "reading": r}, indent=1, sort_keys=True) + "\n")
    print((out / "by_config_type.tsv").read_text())
    print(json.dumps(r, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
