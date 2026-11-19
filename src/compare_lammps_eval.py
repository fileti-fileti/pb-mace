#!/usr/bin/env python3
"""LAMMPS (pair_style mace) vs mace_eval_configs on one frame: a check before the MLMD.

    python3 src/compare_lammps_eval.py DIR

DIR is a system dir of a `prep_mlmd.py --check` run, after its job: log.lammps (line
"PE_START <eV>" after `run 0`, and the "Performance: ... timesteps/s" line of the short
NVT run), forces.dump (LAMMPS custom dump at step 0: id element fx fy fz, sorted by id) and
eval.xyz (mace_eval_configs on start.extxyz: MACE_energy, MACE_forces). Prints one TSV line:
system, n_atoms, |dE|/N (eV/atom), max |dF| over all components (eV/A), timesteps/s, PASS
or FAIL. PASS: |dE|/N <= 1e-6 eV/atom and max |dF| <= 1e-5 eV/A (docs/rdf-mlmd-vs-aimd.md,
checks before production). Exit 1 if a file is missing or the frames do not match.
Standard library only; runs on Python >= 3.6.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mace_errors as me  # noqa: E402

TOL_E, TOL_F = 1e-6, 1e-5
PE_RE = re.compile(r"^PE_START\s+(\S+)")
PERF_RE = re.compile(r"^Performance:.*?([0-9.eE+-]+)\s+timesteps/s")


class CheckError(Exception):
    pass


def read_log(path):
    pe, perf = None, None
    with open(path) as f:
        for line in f:
            m = PE_RE.match(line)
            if m:
                pe = float(m.group(1))
            m = PERF_RE.match(line)
            if m:
                perf = float(m.group(1))   # the last run: the short NVT run
    if pe is None:
        raise CheckError("{}: no PE_START line".format(path))
    return pe, perf


def read_dump(path):
    """-> (elements, forces) of the first snapshot, sorted by id."""
    with open(path) as f:
        lines = f.read().splitlines()
    try:
        n = int(lines[lines.index("ITEM: NUMBER OF ATOMS") + 1])
        k = next(i for i, l in enumerate(lines) if l.startswith("ITEM: ATOMS"))
    except (ValueError, StopIteration, IndexError):
        raise CheckError("{}: not a LAMMPS custom dump".format(path))
    cols = lines[k].split()[2:]
    if cols != ["id", "element", "fx", "fy", "fz"]:
        raise CheckError("{}: columns {} (want id element fx fy fz)".format(path, cols))
    rows = sorted((int(t[0]), t[1], tuple(float(x) for x in t[2:5]))
                  for t in (l.split() for l in lines[k + 1:k + 1 + n]))
    if len(rows) != n or [r[0] for r in rows] != list(range(1, n + 1)):
        raise CheckError("{}: ids are not 1..{}".format(path, n))
    return [r[1] for r in rows], [r[2] for r in rows]


def compare(d):
    pe, perf = read_log(os.path.join(d, "log.lammps"))
    el, f_lmp = read_dump(os.path.join(d, "forces.dump"))
    ev = me.read_extxyz(os.path.join(d, "eval.xyz"))
    if len(ev) != 1:
        raise CheckError("{}: {} frames in eval.xyz, want 1".format(d, len(ev)))
    fr = ev[0]
    if fr["species"] != el:
        raise CheckError("{}: element order differs between LAMMPS and eval.xyz".format(d))
    e_ev = float(fr["info"]["MACE_energy"])
    f_ev = fr["arrays"]["MACE_forces"]
    n = len(el)
    de = abs(pe - e_ev) / n
    dfmax = max(abs(a - b) for fa, fb in zip(f_lmp, f_ev) for a, b in zip(fa, fb))
    ok = de <= TOL_E and dfmax <= TOL_F
    return [os.path.basename(os.path.normpath(d)), str(n), "{:.3e}".format(de),
            "{:.3e}".format(dfmax), "NA" if perf is None else "{:.3f}".format(perf),
            "PASS" if ok else "FAIL"]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    try:
        row = compare(argv[0])
    except (CheckError, me.MetricsError, OSError, ValueError, KeyError) as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1
    print("\t".join(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
