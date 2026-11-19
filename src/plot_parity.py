#!/usr/bin/env python3
"""Parity plots of a MACE model on a labelled extxyz set (figures for claims ID-1, ID-2).

    <env>/bin/python src/plot_parity.py EVAL.xyz REF.xyz OUTDIR [--title TEXT]

EVAL.xyz is the `mace_eval_configs` output for REF.xyz; frames are read and matched by
src/mace_errors.py (same checks: count, species, positions, config_type). Writes
OUTDIR/parity.png:
  (a) energy per atom, predicted vs reference, both minus the mean reference energy per
      atom of the frame's composition (5 compositions here; the E0s are a least-squares
      fit, docs/mace-training.md): spread within a composition and any per-composition bias;
  (b) force components, predicted vs reference (log-density hexbin);
  (c) distribution of the force-component errors per element (log scale);
  (d) force RMSE and MAE per config_type (number of frames in brackets);
and OUTDIR/forces_by_element.png (force parity per element). Values on the figures are
computed here from the same frames as src/mace_errors.py (energy error = dE/N_atoms; force
errors over every Cartesian component). OUTDIR must not exist.
Needs numpy and matplotlib (mace_env).
"""
import argparse
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mace_errors as me  # noqa: E402


def collect(eval_path, ref_path, ref_prefix="REF_", pred_prefix="MACE_"):
    """-> dict of arrays: per frame (ctype, comp, n, e_ref, e_pred per atom, eV) and per atom
    (species, frame index, f_ref, f_pred in eV/A, shape (n_atoms, 3))."""
    ev, rf = me.read_extxyz(eval_path), me.read_extxyz(ref_path)
    me.frame_errors(ev, rf, ref_prefix, pred_prefix)   # raises MetricsError on any mismatch
    out = {k: [] for k in ("ctype", "comp", "n", "e_ref", "e_pred", "species", "frame",
                           "f_ref", "f_pred")}
    for k, (e, r) in enumerate(zip(ev, rf)):
        n = len(r["species"])
        out["ctype"].append(r["info"]["config_type"])
        out["comp"].append(tuple(sorted(Counter(r["species"]).items())))
        out["n"].append(n)
        out["e_ref"].append(float(r["info"][ref_prefix + "energy"]) / n)
        out["e_pred"].append(float(e["info"][pred_prefix + "energy"]) / n)
        out["species"].extend(r["species"])
        out["frame"].extend([k] * n)
        out["f_ref"].extend(r["arrays"][ref_prefix + "forces"])
        out["f_pred"].extend(e["arrays"][pred_prefix + "forces"])
    for k in ("n", "e_ref", "e_pred", "frame", "f_ref", "f_pred"):
        out[k] = np.asarray(out[k], dtype=float if k not in ("n", "frame") else int)
    out["ctype"], out["species"] = np.asarray(out["ctype"]), np.asarray(out["species"])
    return out


def centred_energies(d):
    """E/N minus the mean reference E/N of the frame's composition (eV/atom)."""
    shift = np.empty(len(d["comp"]))
    for c in set(d["comp"]):
        idx = [k for k, ck in enumerate(d["comp"]) if ck == c]
        shift[idx] = d["e_ref"][idx].mean()
    return d["e_ref"] - shift, d["e_pred"] - shift


def rmse_mae(x):
    x = np.asarray(x, dtype=float).ravel()
    return float(np.sqrt(np.mean(x * x))), float(np.mean(np.abs(x)))


def parity_axes(ax, ref, pred, label, unit, hexbin):
    lo, hi = float(min(ref.min(), pred.min())), float(max(ref.max(), pred.max()))
    pad = 0.03 * (hi - lo or 1.0)
    lo, hi = lo - pad, hi + pad
    if hexbin:
        hb = ax.hexbin(ref, pred, gridsize=120, bins="log", mincnt=1, cmap="viridis",
                       extent=(lo, hi, lo, hi))
        ax.figure.colorbar(hb, ax=ax, label="count")
    ax.plot([lo, hi], [lo, hi], color="k", lw=0.7)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    r, m = rmse_mae(pred - ref)
    ax.text(0.04, 0.96, "RMSE {:.1f}\nMAE {:.1f} {}".format(1e3 * r, 1e3 * m, unit),
            transform=ax.transAxes, va="top", fontsize=8,
            bbox=dict(facecolor="white", alpha=0.8, lw=0))
    ax.set_xlabel("reference " + label)
    ax.set_ylabel("MACE " + label)


def plot(d, outdir, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    elements = sorted(set(d["species"]))
    ctypes = sorted(set(d["ctype"]))
    df = d["f_pred"] - d["f_ref"]
    fig, ax = plt.subplots(2, 2, figsize=(13, 11.5))
    a = ax[0, 0]
    er, ep = centred_energies(d)
    cmap = plt.get_cmap("tab20")
    for k, ct in enumerate(ctypes):
        s = d["ctype"] == ct
        a.scatter(er[s], ep[s], s=9, color=cmap(k % 20), label=ct)
    parity_axes(a, er, ep, "E/N − ⟨E_ref/N⟩_composition (eV/atom)", "meV/atom", False)
    a.legend(fontsize=6, ncol=2, loc="lower right", markerscale=1.5)
    a.set_title("(a) energy per atom", fontsize=10)
    parity_axes(ax[0, 1], d["f_ref"].ravel(), d["f_pred"].ravel(), "force component (eV/Å)",
                "meV/Å", True)
    ax[0, 1].set_title("(b) force components", fontsize=10)
    a = ax[1, 0]
    edges = np.linspace(0, max(1e-3, float(np.abs(df).max())) * 1e3, 80)
    for el in elements:
        s = d["species"] == el
        a.hist(1e3 * np.abs(df[s]).ravel(), bins=edges, histtype="step", density=True,
               label="{} (RMSE {:.0f})".format(el, 1e3 * rmse_mae(df[s])[0]))
    a.set_yscale("log")
    a.set_xlabel("|F_MACE − F_ref| per component (meV/Å)")
    a.set_ylabel("probability density")
    a.legend(fontsize=8)
    a.set_title("(c) force-component errors per element", fontsize=10)
    a = ax[1, 1]
    rows = []
    for ct in ctypes:
        s = d["ctype"][d["frame"]] == ct
        rows.append((ct, int(np.sum(d["ctype"] == ct))) + rmse_mae(1e3 * df[s]))
    y = np.arange(len(rows))
    a.barh(y + 0.2, [r[2] for r in rows], height=0.4, label="RMSE")
    a.barh(y - 0.2, [r[3] for r in rows], height=0.4, label="MAE")
    a.set_yticks(y)
    a.set_yticklabels(["{} [{}]".format(r[0], r[1]) for r in rows], fontsize=7)
    a.invert_yaxis()
    a.set_xlabel("force error (meV/Å)")
    a.legend(fontsize=8)
    a.grid(axis="x", alpha=0.3)
    a.set_title("(d) force errors per config_type [frames]", fontsize=10)
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "parity.png"), dpi=150)
    plt.close(fig)

    ncol = 3
    nrow = -(-len(elements) // ncol)
    fig, ax = plt.subplots(nrow, ncol, figsize=(5 * ncol, 4.4 * nrow), squeeze=False)
    for k, el in enumerate(elements):
        s = d["species"] == el
        parity_axes(ax[k // ncol, k % ncol], d["f_ref"][s].ravel(), d["f_pred"][s].ravel(),
                    "force component (eV/Å)", "meV/Å", True)
        ax[k // ncol, k % ncol].set_title("{} ({} atoms)".format(el, int(s.sum())), fontsize=10)
    for k in range(len(elements), nrow * ncol):
        ax[k // ncol, k % ncol].axis("off")
    fig.suptitle(title + " — forces per element", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "forces_by_element.png"), dpi=150)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("eval_xyz")
    ap.add_argument("ref_xyz")
    ap.add_argument("outdir")
    ap.add_argument("--title", default="")
    ap.add_argument("--ref-prefix", default="REF_")
    ap.add_argument("--pred-prefix", default="MACE_")
    a = ap.parse_args(argv)
    try:
        if os.path.exists(a.outdir):
            raise me.MetricsError("{}: exists; pick a new OUTDIR".format(a.outdir))
        d = collect(a.eval_xyz, a.ref_xyz, a.ref_prefix, a.pred_prefix)
    except (me.MetricsError, OSError) as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1
    os.makedirs(a.outdir)
    plot(d, a.outdir, a.title or os.path.basename(os.path.dirname(os.path.abspath(a.eval_xyz))))
    print("wrote {}/parity.png and forces_by_element.png ({} frames, {} atoms)".format(
        a.outdir, len(d["n"]), int(d["n"].sum())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
