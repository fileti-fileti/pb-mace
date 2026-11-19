#!/usr/bin/env python3
"""Training curves of one MACE model, possibly over a chain of runs (monitoring, not a claim).

    <env>/bin/python src/plot_training.py OUTDIR RUN1_train.txt [RUN2_train.txt ...]

Each RUN*_train.txt is MACE's JSON-lines log (`MACE_models/<name>_run-<seed>_train.txt`):
"opt" lines hold one training-batch loss each, "eval" lines the validation metrics after an
epoch ("epoch": null is the evaluation of the starting model, skipped). Later files continue
earlier ones (`--init-checkpoint`); a continued run trains its first epoch index again, so
the x axis counts epochs trained: epoch e of run k is plotted at (epochs of runs before k)
+ (e - first epoch of run k) + 1.

Writes OUTDIR/curves.tsv (one row per epoch trained: run, epoch, validation loss, energy
RMSE/MAE in meV/atom, force RMSE/MAE in meV/A, mean training-batch loss) and
OUTDIR/training.png. Prints, per run, the best validation epoch, the longest run of epochs
without a validation-loss improvement, and the relative change of the validation force RMSE
over the last 50 and 100 epochs trained. The training-batch loss is the mean of the batch
losses of the live (non-EMA) weights while they change; the validation loss uses the EMA
weights: their gap is indicative only. OUTDIR must not exist.
Parsing is standard library; the figure needs matplotlib.
"""
import json
import os
import sys

COLUMNS = ("run", "epoch", "epochs_trained", "valid_loss", "E_RMSE_meV_per_atom",
           "E_MAE_meV_per_atom", "F_RMSE_meV_per_A", "F_MAE_meV_per_A", "train_batch_loss")


class CurveError(Exception):
    pass


def read_train_txt(path):
    """-> (eval rows by epoch, mean opt loss by epoch)."""
    evals, opt = {}, {}
    with open(path) as f:
        for k, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except ValueError as e:
                raise CurveError("{} line {}: {}".format(path, k, e))
            if d.get("epoch") is None:
                continue
            ep = int(d["epoch"])
            if d.get("mode") == "eval":
                if ep in evals:
                    raise CurveError("{}: two eval lines for epoch {}".format(path, ep))
                evals[ep] = d
            elif d.get("mode") == "opt":
                s = opt.setdefault(ep, [0.0, 0])
                s[0] += float(d["loss"])
                s[1] += 1
    if not evals:
        raise CurveError("{}: no eval line with an epoch".format(path))
    return evals, {ep: s[0] / s[1] for ep, s in opt.items()}


def curves(paths):
    """-> list of rows (dicts, COLUMNS keys), epochs trained counted across the chain."""
    rows, done = [], 0
    for path in paths:
        evals, opt = read_train_txt(path)
        eps = sorted(evals)
        if eps != list(range(eps[0], eps[-1] + 1)):
            raise CurveError("{}: eval epochs not contiguous".format(path))
        run = os.path.basename(path).replace("_train.txt", "")
        for ep in eps:
            d = evals[ep]
            rows.append({
                "run": run, "epoch": ep, "epochs_trained": done + ep - eps[0] + 1,
                "valid_loss": float(d["loss"]),
                "E_RMSE_meV_per_atom": 1e3 * float(d["rmse_e_per_atom"]),
                "E_MAE_meV_per_atom": 1e3 * float(d["mae_e_per_atom"]),
                "F_RMSE_meV_per_A": 1e3 * float(d["rmse_f"]),
                "F_MAE_meV_per_A": 1e3 * float(d["mae_f"]),
                "train_batch_loss": opt.get(ep, float("nan")),
            })
        done += len(eps)
    return rows


def summary(rows):
    """-> per run: best epoch and loss, longest no-improvement streak, F RMSE changes."""
    out = []
    for run in sorted({r["run"] for r in rows}, key=[r["run"] for r in rows].index):
        sel = [r for r in rows if r["run"] == run]
        best, streak, longest = None, 0, 0
        for r in sel:
            if best is None or r["valid_loss"] < best["valid_loss"]:
                best, streak = r, 0
            else:
                streak += 1
                longest = max(longest, streak)
        s = {"run": run, "first_epoch": sel[0]["epoch"], "last_epoch": sel[-1]["epoch"],
             "best_epoch": best["epoch"], "best_valid_loss": best["valid_loss"],
             "best_F_RMSE": best["F_RMSE_meV_per_A"],
             "best_E_RMSE": best["E_RMSE_meV_per_atom"], "longest_no_improvement": longest}
        last = rows.index(sel[-1])
        for w in (50, 100):
            if last - w >= 0:
                a, b = rows[last - w]["F_RMSE_meV_per_A"], sel[-1]["F_RMSE_meV_per_A"]
                s["F_RMSE_change_last_{}".format(w)] = (b - a) / a
        out.append(s)
    return out


def plot(rows, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = [r["epochs_trained"] for r in rows]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    ax[0].plot(x, [r["train_batch_loss"] for r in rows], lw=0.8, color="0.6",
               label="training batches (mean, live weights)")
    ax[0].plot(x, [r["valid_loss"] for r in rows], lw=1.2, color="C0",
               label="validation (EMA weights)")
    ax[0].set_yscale("log")
    ax[0].set_ylabel("loss")
    ax[1].plot(x, [r["F_RMSE_meV_per_A"] for r in rows], color="C0", label="RMSE")
    ax[1].plot(x, [r["F_MAE_meV_per_A"] for r in rows], color="C1", label="MAE")
    ax[1].set_ylabel("validation force error (meV/Å)")
    ax[2].plot(x, [r["E_RMSE_meV_per_atom"] for r in rows], color="C0", label="RMSE")
    ax[2].plot(x, [r["E_MAE_meV_per_atom"] for r in rows], color="C1", label="MAE")
    ax[2].set_ylabel("validation energy error (meV/atom)")
    ax[2].set_yscale("log")
    for s in summary(rows):
        xb = next(r["epochs_trained"] for r in rows
                  if r["run"] == s["run"] and r["epoch"] == s["best_epoch"])
        for a in ax:
            a.axvline(xb, color="k", lw=0.6, ls=":")
    starts = [r["epochs_trained"] for k, r in enumerate(rows)
              if k and r["run"] != rows[k - 1]["run"]]
    for a in ax:
        for xs in starts:
            a.axvline(xs - 0.5, color="C3", lw=0.8, ls="--")
        a.set_xlabel("epochs trained")
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.suptitle("dotted: saved (best validation) epoch of each run; dashed: continuation",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(png, dpi=150)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    outdir, paths = argv[0], argv[1:]
    try:
        if os.path.exists(outdir):
            raise CurveError("{}: exists; pick a new OUTDIR".format(outdir))
        rows = curves(paths)
    except (CurveError, OSError) as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1
    os.makedirs(outdir)
    with open(os.path.join(outdir, "curves.tsv"), "w") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for r in rows:
            f.write("\t".join(r[c] if c == "run" else str(r[c]) if c in ("epoch",
                    "epochs_trained") else "{:.6g}".format(r[c]) for c in COLUMNS) + "\n")
    for s in summary(rows):
        print("\t".join("{}={}".format(k, "{:.4g}".format(v) if isinstance(v, float) else v)
                        for k, v in s.items()))
    plot(rows, os.path.join(outdir, "training.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
