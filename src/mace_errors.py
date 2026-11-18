#!/usr/bin/env python3
"""Energy and force errors of a MACE model on a labelled extxyz set (claims ID-1, ID-2).

    python3 src/mace_errors.py EVAL.xyz REF.xyz OUTDIR [--ref-prefix REF_] [--pred-prefix MACE_]

EVAL.xyz is the `mace_eval_configs` output for REF.xyz (the labelled input set, e.g.
data/consolidado/test.xyz). Reference values are read from REF.xyz and predictions from
EVAL.xyz; the two files must hold the same frames in the same order (count, species,
positions within 1e-6 A, config_type), else nothing is written.

Writes OUTDIR/errors.tsv (scope, group, n_frames, n_atoms, energy RMSE and MAE in
meV/atom, force RMSE and MAE in meV/A) for the whole set, each config_type and each
element, and OUTDIR/frame_errors.tsv (one row per frame). OUTDIR must not exist.

Definitions, as in MACE's error tables (mace/tools/utils.py, 0.3.15): energy error of a
frame = (E_pred - E_ref) / N_atoms; RMSE and MAE over frames. Force errors over every
Cartesian component of every atom: RMSE = sqrt(mean dF^2), MAE = mean |dF|. Per element:
forces only (energy is a per-frame quantity), so its energy columns are NA.
Standard library only; runs on Python >= 3.6.
"""
import argparse
import math
import os
import re
import sys

KV_RE = re.compile(r'([A-Za-z_][\w-]*)=("([^"]*)"|\S+)')
POS_TOL = 1e-6   # A; both files carry positions with 8 decimals
COLUMNS = ("scope", "group", "n_frames", "n_atoms", "E_RMSE_meV_per_atom",
           "E_MAE_meV_per_atom", "F_RMSE_meV_per_A", "F_MAE_meV_per_A")


class MetricsError(Exception):
    pass


def parse_comment(line):
    """extxyz comment line -> {key: value string}; quoted values lose their quotes."""
    return {m.group(1): m.group(3) if m.group(3) is not None else m.group(2)
            for m in KV_RE.finditer(line)}


def parse_properties(spec, where):
    """'species:S:1:pos:R:3' -> [('species', 'S', 1), ('pos', 'R', 3)]."""
    t = (spec or "").split(":")
    if len(t) < 3 or len(t) % 3:
        raise MetricsError("{}: bad Properties {!r}".format(where, spec))
    return [(t[i], t[i + 1], int(t[i + 2])) for i in range(0, len(t), 3)]


def read_extxyz(path):
    """-> list of frames {info, species, arrays: {name: [tuple per atom]}} (R columns only)."""
    frames = []
    with open(path) as f:
        lines = iter(f)
        for first in lines:
            if not first.strip():
                continue
            where = "{} frame {}".format(path, len(frames))
            try:
                n = int(first)
                info = parse_comment(next(lines))
                props = parse_properties(info.get("Properties"), where)
                width = sum(c for _, _, c in props)
                species, arrays = [], {name: [] for name, kind, _ in props if kind == "R"}
                for _ in range(n):
                    t = next(lines).split()
                    if len(t) != width:
                        raise MetricsError("{}: {} columns, Properties say {}".format(
                            where, len(t), width))
                    i = 0
                    for name, kind, c in props:
                        if name == "species":
                            species.append(t[i])
                        elif kind == "R":
                            arrays[name].append(tuple(float(v) for v in t[i:i + c]))
                        i += c
            except StopIteration:
                raise MetricsError("{}: file ends inside the frame".format(where))
            except ValueError as e:
                raise MetricsError("{}: {}".format(where, e))
            frames.append({"info": info, "species": species, "arrays": arrays})
    return frames


def need(frame, key, kind, where):
    src = frame["info"] if kind == "info" else frame["arrays"]
    if key not in src:
        raise MetricsError("{}: no {} {!r}".format(where, kind, key))
    return float(src[key]) if kind == "info" else src[key]


def frame_errors(eval_frames, ref_frames, ref_prefix="REF_", pred_prefix="MACE_"):
    """Check the frames match -> per frame (config_type, n, species, dE/N, [dF components])."""
    if len(eval_frames) != len(ref_frames):
        raise MetricsError("{} eval frames vs {} reference frames".format(
            len(eval_frames), len(ref_frames)))
    out = []
    for k, (ev, rf) in enumerate(zip(eval_frames, ref_frames)):
        where = "frame {}".format(k)
        if ev["species"] != rf["species"] or not rf["species"]:
            raise MetricsError("{}: species differ".format(where))
        for a, b in zip(need(ev, "pos", "array", where), need(rf, "pos", "array", where)):
            if max(abs(x - y) for x, y in zip(a, b)) > POS_TOL:
                raise MetricsError("{}: positions differ".format(where))
        ctype = rf["info"].get("config_type")
        if ctype is None or ev["info"].get("config_type") != ctype:
            raise MetricsError("{}: config_type missing or different".format(where))
        n = len(rf["species"])
        de = (need(ev, pred_prefix + "energy", "info", where)
              - need(rf, ref_prefix + "energy", "info", where)) / n
        fp = need(ev, pred_prefix + "forces", "array", where)
        fr = need(rf, ref_prefix + "forces", "array", where)
        df = [[p - r for p, r in zip(a, b)] for a, b in zip(fp, fr)]
        out.append({"config_type": ctype, "n": n, "species": rf["species"], "de": de, "df": df})
    return out


def rmse_mae(values):
    return (math.sqrt(sum(v * v for v in values) / len(values)),
            sum(abs(v) for v in values) / len(values))


def summarize(frames):
    """-> rows of COLUMNS (values in meV/atom and meV/A)."""
    def row(scope, group, sel, element=None):
        f_all = [c for fr in sel for sp, d in zip(fr["species"], fr["df"])
                 if element in (None, sp) for c in d]
        n_atoms = len(f_all) // 3
        fr_ = rmse_mae(f_all)
        if element is None:
            er = rmse_mae([fr["de"] for fr in sel])
            e_cols = ["{:.3f}".format(1e3 * x) for x in er]
            n_frames = str(len(sel))
        else:
            e_cols, n_frames = ["NA", "NA"], str(sum(element in fr["species"] for fr in sel))
        return [scope, group, n_frames, str(n_atoms)] + e_cols + [
            "{:.3f}".format(1e3 * x) for x in fr_]

    rows = [row("all", "all", frames)]
    for ct in sorted({fr["config_type"] for fr in frames}):
        rows.append(row("config_type", ct, [fr for fr in frames if fr["config_type"] == ct]))
    for el in sorted({sp for fr in frames for sp in fr["species"]}):
        rows.append(row("element", el, frames, element=el))
    return rows


def write_tsv(path, header, rows):
    with open(path, "w") as f:
        f.write("\t".join(header) + "\n")
        for r in rows:
            f.write("\t".join(r) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("eval_xyz")
    ap.add_argument("ref_xyz")
    ap.add_argument("outdir")
    ap.add_argument("--ref-prefix", default="REF_")
    ap.add_argument("--pred-prefix", default="MACE_")
    a = ap.parse_args(argv)
    try:
        if os.path.exists(a.outdir):
            raise MetricsError("{}: exists; pick a new OUTDIR".format(a.outdir))
        frames = frame_errors(read_extxyz(a.eval_xyz), read_extxyz(a.ref_xyz),
                              a.ref_prefix, a.pred_prefix)
    except (MetricsError, OSError) as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1
    rows = summarize(frames)
    os.makedirs(a.outdir)
    write_tsv(os.path.join(a.outdir, "errors.tsv"), COLUMNS, rows)
    write_tsv(os.path.join(a.outdir, "frame_errors.tsv"),
              ("frame", "config_type", "n_atoms", "dE_meV_per_atom", "F_RMSE_meV_per_A"),
              [[str(k), fr["config_type"], str(fr["n"]), "{:.3f}".format(1e3 * fr["de"]),
                "{:.3f}".format(1e3 * rmse_mae([c for d in fr["df"] for c in d])[0])]
               for k, fr in enumerate(frames)])
    for r in rows:
        print("\t".join(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
