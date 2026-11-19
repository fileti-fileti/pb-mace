#!/usr/bin/env python3
"""MLMD vs AIMD RDF comparison: the reading rule of docs/rdf-mlmd-vs-aimd.md (fixed 2026-11-19).

    <env>/bin/python src/rdf_compare.py AIMD_DIR MLMD_DIR OUTDIR --replicas R [--unstable LIST]

AIMD_DIR: the registered AIMD reference (results/aimd-rdf-reference/): rdf_<sys>_<A>-<B>.dat
(r g g_err n). MLMD_DIR: src/rdf.py output of the replicas, systems named <sys>_r<k>
(k = 1..R), with their _blocks.dat. --unstable: comma-separated <sys>_r<k> replicas that
lost atoms or gave non-finite values (prep_mlmd.py UNSTABLE).

Per system and pair:
- first peak: from contact to r_c, the first local minimum after the first local maximum of
  the AIMD's g on its 5-bin running mean (same window for every curve); no minimum: the
  window runs to r_max and n1 is not used; no maximum: the pair has no quantity (NA);
- r1: position of the highest bin of g in the window, refined by the parabola through it and
  its two neighbours; n1: n at the upper edge of the r_c bin; g1: g of the highest bin
  (reported, no verdict);
- AIMD value from its curve; MLMD: mean over the replicas, s = their standard deviation;
  sigma = s * sqrt(1 + 1/R) (s stands for one AIMD-length run; the registered AIMD files
  hold no per-block curves); delta = AIMD - MLMD mean. Reported, no part of the rule: the
  AIMD's g_err at the g1 bin and the MLMD's own 5-block error of each quantity (mean over
  the replicas, from their _blocks.dat: the check of limit 6);
- tolerance: r1 0.05 A, n1 5 % of the AIMD value; verdict yes if |delta| + 2 sigma <= tol,
  no if |delta| - 2 sigma > tol, else inconclusive;
- pair: no if any quantity is no, yes if all are yes, else inconclusive (NA without r1);
- group (framework, water, Na) per system: no if any pair is no or any replica of the system
  is unstable, yes if all pairs are yes, else inconclusive.
Writes OUTDIR/compare.tsv (one row per system, pair and quantity), OUTDIR/verdicts.tsv (one
row per system and group) and OUTDIR/compare_info.json (commit, inputs); refuses a dirty
tree and an existing OUTDIR. Needs numpy.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMOOTH = 5
TOL_R1 = 0.05      # A
TOL_N1 = 0.05      # fraction of the AIMD value
GROUPS = {
    "framework": ("Fe2-C", "Fe3-N", "C-N", "Fe2-Fe3"),
    "water": ("O-O", "O-H", "Fe3-O", "N-H"),
    "Na": ("Na-N", "Na-C", "Na-O"),
}
DAT_RE = re.compile(r"^rdf_(.+)_([A-Z][a-z]?\d?-[A-Z][a-z]?\d?)\.dat$")


def group_of(pair):
    for g, pairs in GROUPS.items():
        if pair in pairs:
            return g
    raise ValueError("pair {} is in no group of the reading rule".format(pair))


def running_mean(g, w=SMOOTH):
    k = np.ones(w)
    return np.convolve(g, k, mode="same") / np.convolve(np.ones_like(g), k, mode="same")


def first_peak_window(g):
    """-> (i_max, j_min) on the running mean of g; None where absent."""
    s = running_mean(np.asarray(g, dtype=float))
    imax = next((i for i in range(1, len(s) - 1)
                 if s[i] > 0 and s[i] >= s[i - 1] and s[i] > s[i + 1]), None)
    if imax is None:
        return None, None
    jmin = next((j for j in range(imax + 1, len(s) - 1)
                 if s[j] <= s[j - 1] and s[j] < s[j + 1]), None)
    return imax, jmin


def peak_quantities(r, g, n, jmin):
    """-> {r1, g1, n1 (None without jmin)} of one curve in the window [0, jmin]."""
    hi = len(g) - 1 if jmin is None else jmin
    k = int(np.argmax(g[:hi + 1]))
    r1 = r[k]
    if 0 < k < len(g) - 1:
        den = g[k - 1] - 2.0 * g[k] + g[k + 1]
        if den < 0:
            r1 = r[k] + 0.5 * (r[1] - r[0]) * (g[k - 1] - g[k + 1]) / den
    return {"r1": float(r1), "g1": float(g[k]), "n1": None if jmin is None else float(n[jmin])}


def verdict(delta, sigma, tol):
    if abs(delta) + 2 * sigma <= tol:
        return "yes"
    if abs(delta) - 2 * sigma > tol:
        return "no"
    return "inconclusive"


def combine(verdicts):
    v = [x for x in verdicts if x is not None]
    if not v or all(x == "NA" for x in v):
        return "NA"
    if "no" in v:
        return "no"
    if all(x == "yes" for x in v):
        return "yes"
    return "inconclusive"


def load_dat(path):
    """-> r, g, g_err, n."""
    a = np.loadtxt(path)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]


def load_blocks(path):
    a = np.loadtxt(path)
    nb = (a.shape[1] - 1) // 2
    if a.shape[1] != 2 * nb + 1 or nb < 2:
        raise ValueError("{}: want r, g_1..g_K, n_1..n_K with K >= 2".format(path))
    return a[:, 0], a[:, 1:1 + nb].T, a[:, 1 + nb:].T


def block_err(path, r, jmin, q):
    """5-block error of quantity q of one replica, from its _blocks.dat (None if absent)."""
    pb = path[:-4] + "_blocks.dat"
    if not os.path.isfile(pb):
        return None
    rb, gb, nb = load_blocks(pb)
    if not np.allclose(rb, r):
        raise ValueError("{}: r grid differs".format(pb))
    v = [peak_quantities(r, gb[b], nb[b], jmin)[q] for b in range(len(gb))]
    return float(np.std(v, ddof=1) / np.sqrt(len(v)))


def compare_pair(aimd_dat, mlmd_dats):
    """-> (rows (quantity, aimd, aimd_err, mean, s, sigma, delta, tol, verdict,
    mlmd_block_err), r_c)."""
    r, g, gerr, n = load_dat(aimd_dat)
    imax, jmin = first_peak_window(g)
    if imax is None:
        return [("r1",) + (None,) * 7 + ("NA", None)], None
    ref = peak_quantities(r, g, n, jmin)
    hi = len(g) - 1 if jmin is None else jmin
    g1_err = float(gerr[int(np.argmax(g[:hi + 1]))])
    reps = []
    for p in mlmd_dats:
        rm, gm, _, nm = load_dat(p)
        if not np.allclose(rm, r):
            raise ValueError("{}: r grid differs from {}".format(p, aimd_dat))
        reps.append(peak_quantities(rm, gm, nm, jmin))
    R = len(reps)
    rows = []
    for q in ("r1", "n1", "g1"):
        if ref[q] is None:
            continue
        vals = np.array([x[q] for x in reps])
        mean, s = float(vals.mean()), float(vals.std(ddof=1))
        sigma = s * float(np.sqrt(1.0 + 1.0 / R))
        delta = ref[q] - mean
        be = [block_err(p, r, jmin, q) for p in mlmd_dats]
        mbe = None if any(b is None for b in be) else float(np.mean(be))
        if q == "g1":
            tol, v, e = None, "descriptive", g1_err
        else:
            tol = TOL_R1 if q == "r1" else TOL_N1 * abs(ref[q])
            v, e = verdict(delta, sigma, tol), None
        rows.append((q, ref[q], e, mean, s, sigma, delta, tol, v, mbe))
    return rows, r[jmin] if jmin is not None else None


def find_pairs(aimd_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(aimd_dir, "rdf_*.dat"))):
        m = DAT_RE.match(os.path.basename(p))
        if m and not p.endswith("_blocks.dat"):
            out.append((m.group(1), m.group(2)))
    if not out:
        raise ValueError("{}: no rdf_<system>_<A>-<B>.dat".format(aimd_dir))
    return out


def run(aimd_dir, mlmd_dir, replicas, unstable):
    """-> (compare rows, verdict rows). Unstable replicas are left out of the statistics and
    make every group of their system "no"."""
    comp, groups = [], {}
    for system, pair in find_pairs(aimd_dir):
        group = group_of(pair)
        names = ["{}_r{}".format(system, k) for k in range(1, replicas + 1)]
        mlmd = [os.path.join(mlmd_dir, "rdf_{}_{}.dat".format(nm, pair))
                for nm in names if nm not in unstable]
        missing = [p for p in mlmd if not os.path.isfile(p)]
        if missing:
            raise ValueError("missing MLMD files: {}".format(", ".join(missing)))
        if len(mlmd) < 2:   # too few stable replicas for a spread
            rows, rc = [("r1",) + (None,) * 7 + ("no", None)], None
        else:
            rows, rc = compare_pair(
                os.path.join(aimd_dir, "rdf_{}_{}.dat".format(system, pair)), mlmd)
        comp += [(system, pair, group, rc) + row for row in rows]
        pv = combine([row[8] for row in rows if row[0] != "g1"])
        groups.setdefault((system, group), []).append((pair, pv))
    ver = []
    for (system, group), pairs in groups.items():
        unst = [u for u in unstable if u.rsplit("_r", 1)[0] == system]
        v = "no" if unst else combine([pv for _, pv in pairs])
        ver.append((system, group, v, " ".join("{}:{}".format(p, pv) for p, pv in pairs),
                    ",".join(unst)))
    return comp, ver


def fmt(x):
    return "NA" if x is None else ("{:.6g}".format(x) if isinstance(x, float) else str(x))


def git_commit():
    dirty = subprocess.check_output(["git", "-C", REPO, "status", "--porcelain"]).decode()
    if dirty.strip():
        sys.exit("dirty tree: commit first (results record the exact commit)\n" + dirty)
    return subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"]).decode().strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("aimd_dir")
    ap.add_argument("mlmd_dir")
    ap.add_argument("outdir")
    ap.add_argument("--replicas", type=int, required=True)
    ap.add_argument("--unstable", default="")
    a = ap.parse_args(argv)
    if os.path.exists(a.outdir):
        sys.exit("{}: exists; pick a new OUTDIR".format(a.outdir))
    commit = git_commit()
    unstable = [u for u in a.unstable.split(",") if u]
    comp, ver = run(a.aimd_dir, a.mlmd_dir, a.replicas, unstable)
    os.makedirs(a.outdir)
    with open(os.path.join(a.outdir, "compare.tsv"), "w") as f:
        f.write("system\tpair\tgroup\tr_c\tquantity\taimd\taimd_err\tmlmd_mean\tmlmd_sd\t"
                "sigma\tdelta\ttolerance\tverdict\tmlmd_block_err\n")
        for row in comp:
            f.write("\t".join(fmt(x) for x in row) + "\n")
    with open(os.path.join(a.outdir, "verdicts.tsv"), "w") as f:
        f.write("system\tgroup\tverdict\tpairs\tunstable_replicas\n")
        for row in ver:
            f.write("\t".join(row) + "\n")
            print("\t".join(row[:3]))
    with open(os.path.join(a.outdir, "compare_info.json"), "w") as f:
        json.dump({"commit": commit, "aimd_dir": os.path.abspath(a.aimd_dir),
                   "mlmd_dir": os.path.abspath(a.mlmd_dir), "replicas": a.replicas,
                   "unstable": unstable, "smooth_bins": SMOOTH, "tol_r1_A": TOL_R1,
                   "sigma": "s * sqrt(1 + 1/R)",
                   "tol_n1_fraction": TOL_N1, "groups": GROUPS}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
