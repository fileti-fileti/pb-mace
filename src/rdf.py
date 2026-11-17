#!/usr/bin/env python3
"""Partial radial distribution functions g_AB(r) from CP2K trajectories (pb-mace).

Orthorhombic cell, minimum image, r_max <= half the shortest cell edge. Method and
parameters: docs/rdf-mlmd-vs-aimd.md. Needs numpy and matplotlib (neumann: `analysis` env).

    <env>/bin/python src/rdf.py configs/rdf/aimd_reference.json runs/<run dir>

Writes per system `rdf_<system>_<A>-<B>.dat` (r, g, g_err, n) and `rdf_<system>.png`,
plus `run_info.json` (commit, config, frames used, block check). Refuses a dirty tree.
"""
import bisect
import json
import os
import re
import subprocess
import sys

import numpy as np

HEADER = re.compile(r"i\s*=\s*(-?\d+)\s*,\s*time\s*=\s*([-0-9.Ee+]+)")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def element(label):
    """Element of a CP2K kind label: Fe2 -> Fe, Fe3_up -> Fe, Na -> Na."""
    m = re.match(r"[A-Z][a-z]?", label)
    if m is None:
        raise ValueError("not a kind label: {!r}".format(label))
    return m.group(0)


def read_kinds(path):
    """Kind label of each atom, in file order, from a CP2K &COORD include."""
    kinds = []
    with open(path) as f:
        for line in f:
            t = line.split()
            if len(t) < 4 or t[0].startswith(("&", "#", "!")):
                continue
            try:
                [float(x) for x in t[1:4]]
            except ValueError:
                continue
            kinds.append(t[0])
    return kinds


def iter_xyz(path):
    """Yield (step, time_fs, symbols, positions) per frame of a CP2K -pos-1.xyz file.
    A truncated last frame (run killed while writing) is dropped with a warning."""
    with open(path) as f:
        while True:
            line = f.readline()
            if not line.strip():
                return
            n = int(line.split()[0])
            m = HEADER.search(f.readline())
            if m is None:
                raise ValueError("frame without 'i = ..., time = ...' in {}".format(path))
            sym, pos = [], np.empty((n, 3))
            for k in range(n):
                t = f.readline().split()
                if len(t) < 4:
                    print("warning: truncated frame at step {} in {}: dropped".format(
                        m.group(1), path), file=sys.stderr)
                    return
                sym.append(t[0])
                pos[k] = [float(x) for x in t[1:4]]
            yield int(m.group(1)), float(m.group(2)), sym, pos


def stitch(paths):
    """Frames of the files in run order. A frame whose step is <= the last kept step drops
    the kept frames from that step on: after a restart from an earlier checkpoint, the
    last branch through a step wins. Returns (steps, times, symbols, frames)."""
    steps, times, frames, symbols = [], [], [], None
    for p in paths:
        for step, t, sym, pos in iter_xyz(p):
            if symbols is None:
                symbols = sym
            elif sym != symbols:
                raise ValueError("atom order changed in {}".format(p))
            if steps and step <= steps[-1]:
                k = bisect.bisect_left(steps, step)
                del steps[k:], times[k:], frames[k:]
            steps.append(step)
            times.append(t)
            frames.append(pos)
    if symbols is None:
        raise ValueError("no frames in {}".format(paths))
    return np.array(steps), np.array(times), symbols, np.array(frames)


def bin_edges(cell, dr):
    """Bin edges from 0 to half the shortest edge, floored to a whole bin."""
    nbins = int(np.floor(min(cell) / 2.0 / dr + 1e-9))
    return dr * np.arange(nbins + 1)


def pair_counts(frames, ia, ib, cell, edges):
    """Histogram of A-B distances per frame (ordered pairs, self pairs excluded)."""
    L = np.asarray(cell, dtype=float)
    same = np.array_equal(ia, ib)
    off = ~np.eye(len(ia), dtype=bool) if same else None
    counts = np.zeros((len(frames), len(edges) - 1))
    for f, X in enumerate(frames):
        d = X[ib][None, :, :] - X[ia][:, None, :]
        d -= L * np.round(d / L)
        r = np.sqrt((d * d).sum(axis=-1))
        counts[f] = np.histogram(r[off] if same else r, bins=edges)[0]
    return counts


def partial_rdf(frames, ia, ib, cell, edges, nblocks):
    """g_AB(r), its block standard error and n_AB(r) (B neighbours of an A within r)."""
    ia, ib = np.asarray(ia), np.asarray(ib)
    counts = pair_counts(frames, ia, ib, cell, edges)
    same = np.array_equal(ia, ib)
    npairs = len(ia) * (len(ia) - 1) if same else len(ia) * len(ib)
    shell = 4.0 / 3.0 * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    ideal = npairs * shell / float(np.prod(cell))
    g = counts.mean(axis=0) / ideal
    err = block_error(counts, ideal, nblocks)
    n = np.cumsum(counts.mean(axis=0)) / len(ia)
    r = 0.5 * (edges[1:] + edges[:-1])
    return r, g, err, n, counts, ideal


def block_error(counts, ideal, nblocks):
    """Standard error of g over contiguous blocks of frames (NaN with < 2 blocks)."""
    if nblocks < 2 or len(counts) < nblocks:
        return np.full(len(ideal), np.nan)
    blocks = [b.mean(axis=0) / ideal for b in np.array_split(counts, nblocks)]
    return np.std(blocks, axis=0, ddof=1) / np.sqrt(nblocks)


def git_commit():
    dirty = subprocess.check_output(["git", "-C", REPO, "status", "--porcelain"]).decode()
    if dirty.strip():
        sys.exit("dirty tree: commit first (runs record the exact commit)\n" + dirty)
    return subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"]).decode().strip()


def run_system(name, cfg, dr, nblocks, block_check, outdir):
    steps, times, symbols, frames = stitch(cfg["trajectory"])
    kinds = read_kinds(cfg["kinds"])
    if len(kinds) != len(symbols):
        sys.exit("{}: {} kinds vs {} atoms".format(name, len(kinds), len(symbols)))
    bad = [i for i, (k, s) in enumerate(zip(kinds, symbols)) if element(k) != s]
    if bad:
        sys.exit("{}: kind/element mismatch at atoms {}".format(name, bad[:10]))
    keep = times >= cfg["discard_fs"]
    steps, times, frames = steps[keep], times[keep], frames[keep]
    strides = sorted(set(np.diff(steps).tolist()))
    edges = bin_edges(cfg["cell"], dr)
    kinds = np.array(kinds)
    info = {"frames": int(len(frames)), "first_step": int(steps[0]),
            "last_step": int(steps[-1]), "first_time_fs": float(times[0]),
            "last_time_fs": float(times[-1]), "step_strides": strides,
            "r_max": float(edges[-1]), "pairs": {}}
    results = []
    for a, b in cfg["pairs"]:
        ia, ib = np.where(kinds == a)[0], np.where(kinds == b)[0]
        if len(ia) == 0 or len(ib) == 0:
            sys.exit("{}: no atoms of kind {} or {}".format(name, a, b))
        r, g, err, n, counts, ideal = partial_rdf(frames, ia, ib, cfg["cell"], edges, nblocks)
        peak = int(np.argmax(g))
        check = {str(k): float(block_error(counts, ideal, k)[peak]) for k in block_check}
        info["pairs"]["{}-{}".format(a, b)] = {
            "nA": int(len(ia)), "nB": int(len(ib)), "first_peak_r": float(r[peak]),
            "first_peak_g": float(g[peak]), "peak_err_by_nblocks": check}
        path = os.path.join(outdir, "rdf_{}_{}-{}.dat".format(name, a, b))
        head = ("system {} pair {}-{} | frames {} (steps {}-{}, t >= {} fs) | dr {} r_max {} "
                "| err: {} contiguous blocks\nr_A g g_err n_within_r_upper").format(
                    name, a, b, len(frames), steps[0], steps[-1], cfg["discard_fs"], dr,
                    edges[-1], nblocks)
        np.savetxt(path, np.column_stack([r, g, err, n]), fmt="%.6f", header=head)
        results.append((a, b, r, g, err, n))
    plot(name, results, info["frames"], os.path.join(outdir, "rdf_{}.png".format(name)))
    return info


def plot(name, results, nframes, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ncol = 3
    nrow = (len(results) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.0 * nrow), squeeze=False)
    for ax, (a, b, r, g, err, n) in zip(axes.flat, results):
        ax.fill_between(r, g - err, g + err, color="C0", alpha=0.3, lw=0)
        ax.plot(r, g, color="C0", lw=1)
        ax.set_title("{}–{}".format(a, b), fontsize=10)
        ax.set_xlabel("r (Å)")
        ax.set_ylabel("g(r)")
        ax2 = ax.twinx()
        ax2.plot(r, n, color="C1", lw=0.8, ls="--")
        ax2.set_ylabel("n(r)", color="C1")
    for ax in list(axes.flat)[len(results):]:
        ax.axis("off")
    fig.suptitle("{} — AIMD, {} frames".format(name, nframes))
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    cfg_path, outdir = argv[1], argv[2]
    commit = git_commit()
    cfg = json.load(open(cfg_path))
    os.makedirs(outdir, exist_ok=True)
    info = {"commit": commit, "config": os.path.relpath(os.path.abspath(cfg_path), REPO),
            "dr": cfg["dr"], "nblocks": cfg["nblocks"], "systems": {}}
    for name, scfg in cfg["systems"].items():
        info["systems"][name] = run_system(name, scfg, cfg["dr"], cfg["nblocks"],
                                           cfg["block_check"], outdir)
        s = info["systems"][name]
        print("{}: {} frames, steps {}-{}, strides {}, r_max {}".format(
            name, s["frames"], s["first_step"], s["last_step"], s["step_strides"], s["r_max"]))
        for pair, p in s["pairs"].items():
            print("  {:7s} peak r {:.3f} g {:.3f} err(nblocks) {}".format(
                pair, p["first_peak_r"], p["first_peak_g"],
                " ".join("{}:{:.3f}".format(k, v) for k, v in p["peak_err_by_nblocks"].items())))
    with open(os.path.join(outdir, "run_info.json"), "w") as f:
        json.dump(info, f, indent=1)


if __name__ == "__main__":
    main(sys.argv)
