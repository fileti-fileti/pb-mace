#!/usr/bin/env python3
"""Analyse the Na translation test (docs/na-label-grid-error.md, "Translation test").

Usage: python3 src/na_translation.py RUN_DIR [--out DIR]
RUN_DIR: the dir made by scripts/prep_na_translation.py (run_info.json + one dir per run).
Writes DIR/summary.tsv (one row per run), DIR/per_shift.tsv and DIR/verdict.json
(default DIR = RUN_DIR/analysis) and prints the reading.

Reading, as fixed in the doc before submission (commit 2b2f93f):
- s_el: RMS over the atoms of el and the 3 components of the std (population, ddof 0) of the
  force over the valid shifts, meV/A. |SF|max: largest norm of the summed force over the
  valid shifts, meV/A. Valid shift: SCF converged and every Fe Mulliken spin within
  SPIN_TOL of shift 0. Shift 0 not valid, or fewer than MIN_VALID valid shifts: the run is
  inconclusive.
- Check: shift 0 of DIAG_RUN reproduces the legacy label (max |dF| <= REPRO_TOL), else the
  whole test is inconclusive.
- Diagnosis (DIAG_RUN): confirmed if s_Na >= 100 and s_Na >= 5 x max(s_Fe, s_C, s_N);
  refuted if s_Na < 50 or s_Na < 2 x that max; otherwise inconclusive.
- Remedy (each other run of the Na frame): fixed if s_Na <= 2 x max_el s_el and
  |SF|max <= 2 x |SF|max, both of CONTROL_RUN.
- No verdict: s_el and |SF| vs setting; Q1_RUN vs Q1_REF_RUN forces at shift 0.
The grid size N is read from the output (finest PW grid, x axis); the shift phases are
reported against it. Standard library only; runs on Python >= 3.6.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import prep_na_translation as pt  # noqa: E402  (force readers, unit factor)

TO_MEV_A = pt.HA_BOHR_TO_EV_A * 1000.0
HA_TO_MEV = 27211.386245988
SPIN_TOL = 0.3
MIN_VALID = 3
REPRO_TOL = 10.0
DIAG = {"confirm_min": 100.0, "confirm_ratio": 5.0, "refute_min": 50.0, "refute_ratio": 2.0}
FIX_FACTOR = 2.0
NA_FRAME = "cubo_puro"
DIAG_RUN = "cubo_puro-q9-c700"
CONTROL_RUN = "vacancia-q9-c700"
Q1_RUN, Q1_REF_RUN = "cubo_puro-q1-c700", "cubo_puro-q9-c1600"
HOSTS = ("Fe", "C", "N")
ELEMENTS = ("Fe", "C", "N", "Na", "O", "H")

STATUS_RE = re.compile(r"(SCF run converged|SCF run NOT converged|outer SCF loop converged|"
                       r"outer SCF loop FAILED)")
ENERGY_RE = re.compile(r"ENERGY\| Total FORCE_EVAL \( QS \) energy \[a\.u\.\]:\s+(\S+)")


def parse_out(text):
    """CP2K output -> {"ended", "grid_n", "steps": [{"energy", "converged", "fe_spins"}]}.
    Per step (closed by its ENERGY line): the last SCF status message decides convergence;
    the last Mulliken block gives the Fe spin moments {atom index: spin}."""
    grid_n, in_grid1 = None, False
    steps, status, spins, mull, in_mull = [], None, None, None, False
    for line in text.splitlines():
        if "PW_GRID| Information for grid number" in line:
            in_grid1 = line.split()[-1] == "1" and grid_n is None
        elif in_grid1 and "PW_GRID|   Bounds   1" in line:
            grid_n, in_grid1 = int(line.split()[-1]), False
        m = STATUS_RE.search(line)
        if m:
            status = m.group(1) in ("SCF run converged", "outer SCF loop converged")
        if "Mulliken Population Analysis" in line:
            in_mull, mull = True, {}
            continue
        if in_mull:
            t = line.split()
            if line.strip().startswith("# Total charge"):
                in_mull, spins = False, mull
            elif len(t) == 7 and t[0].isdigit() and t[1] == "Fe":
                mull[int(t[0])] = float(t[6])
        m = ENERGY_RE.search(line)
        if m:
            steps.append({"energy": float(m.group(1)), "converged": bool(status),
                          "fe_spins": spins or {}})
            status, spins = None, None
    return {"ended": "PROGRAM ENDED" in text, "grid_n": grid_n, "steps": steps}


def spread_stats(forces, valid):
    """forces: [shift][atom] = (el, fx, fy, fz) in Ha/bohr; valid: [bool] per shift.
    -> ({el: s_el meV/A}, [|SF| meV/A per shift])."""
    use = [f for f, v in zip(forces, valid) if v]
    acc = {}
    for i, atom in enumerate(use[0]):
        el = atom[0]
        for c in (1, 2, 3):
            vals = [f[i][c] for f in use]
            mu = sum(vals) / len(vals)
            var = sum((v - mu) ** 2 for v in vals) / len(vals)
            s, n = acc.get(el, (0.0, 0))
            acc[el] = (s + var, n + 1)
    s_el = {el: math.sqrt(s / n) * TO_MEV_A for el, (s, n) in acc.items()}
    sumf = []
    for f in forces:
        tot = [sum(a[c] for a in f) for c in (1, 2, 3)]
        sumf.append(math.sqrt(sum(x * x for x in tot)) * TO_MEV_A)
    return s_el, sumf


def max_abs_diff(fa, fb):
    if [a[0] for a in fa] != [b[0] for b in fb]:
        raise ValueError("element order differs")
    return max(abs(a[c] - b[c]) for a, b in zip(fa, fb) for c in (1, 2, 3)) * TO_MEV_A


def rms_diff_by_element(fa, fb):
    acc = {}
    for a, b in zip(fa, fb):
        s, n = acc.get(a[0], (0.0, 0))
        acc[a[0]] = (s + sum((a[c] - b[c]) ** 2 for c in (1, 2, 3)), n + 3)
    return {el: math.sqrt(s / n) * TO_MEV_A for el, (s, n) in acc.items()}


def analyse_run(rd, info):
    out = rd / "relabel.out"
    row = {"run": rd.name, "frame": info["frame"], "setting": info["setting"]}
    if not out.is_file():
        row["status"] = "missing"
        return row, None
    p = parse_out(out.read_text())
    nsh = len(info["shifts_A"])
    row.update(ended=p["ended"], grid_n=p["grid_n"], n_steps=len(p["steps"]))
    if not p["ended"] or len(p["steps"]) != nsh:
        row["status"] = "not ended" if not p["ended"] else "steps {} != {}".format(
            len(p["steps"]), nsh)
        return row, None
    ftext = (rd / info["forces_file"]).read_text()
    forces = [pt.read_forces(ftext, k + 1, info["forces_file"]) for k in range(nsh)]
    ref_spins = p["steps"][0]["fe_spins"]
    valid, dspin = [], []
    for st in p["steps"]:
        ds = max([abs(st["fe_spins"].get(i, float("inf")) - s) for i, s in ref_spins.items()]
                 or [0.0])
        dspin.append(ds)
        valid.append(st["converged"] and ds <= SPIN_TOL)
    h = info["cell_A"] / p["grid_n"] if p["grid_n"] else float("nan")
    row.update(h_A=h, phases=[s / h for s in info["shifts_A"]], valid=valid, dspin=dspin,
               energies_meV=[(st["energy"] - p["steps"][0]["energy"]) * HA_TO_MEV
                             for st in p["steps"]])
    if not valid[0] or sum(valid) < MIN_VALID:
        row["status"] = "inconclusive ({} valid shifts)".format(sum(valid))
        return row, forces
    s_el, sumf = spread_stats(forces, valid)
    row.update(status="ok", s_el=s_el, sumF=sumf,
               sumF_max=max(f for f, v in zip(sumf, valid) if v),
               dE_spread_meV=max(e for e, v in zip(row["energies_meV"], valid) if v)
               - min(e for e, v in zip(row["energies_meV"], valid) if v))
    return row, forces


def reading(rows, forces, run_dir):
    r = {"repro": None, "diagnosis": "inconclusive", "remedies": {}, "q1_vs_q9_c1600": None}
    d, c = rows.get(DIAG_RUN), rows.get(CONTROL_RUN)
    if d is None or d.get("status") != "ok":
        r["note"] = "{} not ok".format(DIAG_RUN)
        return r
    ref = pt.read_forces((run_dir / DIAG_RUN / "ref_frc.xyz").read_text(), 1, "ref_frc.xyz")
    r["repro"] = max_abs_diff(forces[DIAG_RUN][0], ref)
    if r["repro"] > REPRO_TOL:
        r["note"] = "shift 0 does not reproduce the legacy label: whole test inconclusive"
        return r
    s = d["s_el"]
    host = max(s[e] for e in HOSTS if e in s)
    r["diag_numbers"] = {"s_Na": s["Na"], "max_host": host, "ratio": s["Na"] / host}
    if s["Na"] >= DIAG["confirm_min"] and s["Na"] >= DIAG["confirm_ratio"] * host:
        r["diagnosis"] = "confirmed"
    elif s["Na"] < DIAG["refute_min"] or s["Na"] < DIAG["refute_ratio"] * host:
        r["diagnosis"] = "refuted"
    if c is None or c.get("status") != "ok":
        r["note"] = "{} not ok: remedies not read".format(CONTROL_RUN)
    else:
        lim_s = FIX_FACTOR * max(c["s_el"].values())
        lim_f = FIX_FACTOR * c["sumF_max"]
        r["remedy_limits"] = {"s_Na_max": lim_s, "sumF_max": lim_f}
        for name, row in sorted(rows.items()):
            if row["frame"] != NA_FRAME or name == DIAG_RUN:
                continue
            if row.get("status") != "ok":
                r["remedies"][name] = "inconclusive ({})".format(row.get("status"))
            else:
                ok = row["s_el"]["Na"] <= lim_s and row["sumF_max"] <= lim_f
                r["remedies"][name] = "fixed" if ok else "not fixed"
    if forces.get(Q1_RUN) and forces.get(Q1_REF_RUN):
        r["q1_vs_q9_c1600"] = rms_diff_by_element(forces[Q1_RUN][0], forces[Q1_REF_RUN][0])
    return r


def fmt(x, nd=1):
    return "-" if x is None else ("{:.%df}" % nd).format(x)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir).resolve()
    info = json.loads((run_dir / "run_info.json").read_text())
    out = Path(a.out) if a.out else run_dir / "analysis"
    rows, forces = {}, {}
    for name, ri in sorted(info["runs"].items()):
        rows[name], forces[name] = analyse_run(run_dir / name, ri)
    r = reading(rows, forces, run_dir)
    out.mkdir(parents=True, exist_ok=True)
    cols = ["run", "status", "grid_n", "h_A", "phases", "valid", "max_dspin",
            "dE_spread_meV", "sumF_max"] + ["s_" + e for e in ELEMENTS]
    lines = ["\t".join(cols)]
    for name, row in sorted(rows.items()):
        se = row.get("s_el", {})
        lines.append("\t".join([
            name, row.get("status", "-"), str(row.get("grid_n", "-")), fmt(row.get("h_A"), 5),
            ",".join("{:.3f}".format(x) for x in row.get("phases", [])),
            "".join("1" if v else "0" for v in row.get("valid", [])),
            fmt(max(row["dspin"]) if row.get("dspin") else None, 3),
            fmt(row.get("dE_spread_meV"), 3), fmt(row.get("sumF_max"))]
            + [fmt(se.get(e)) for e in ELEMENTS]))
    (out / "summary.tsv").write_text("\n".join(lines) + "\n")
    ps = ["run\tshift\tvalid\tdspin\tdE_meV\tsumF_meV_A"]
    for name, row in sorted(rows.items()):
        for k, v in enumerate(row.get("valid", [])):
            ps.append("\t".join([name, str(k), str(int(v)), "{:.3f}".format(row["dspin"][k]),
                                 "{:.3f}".format(row["energies_meV"][k]),
                                 fmt(row["sumF"][k]) if row.get("sumF") else "-"]))
    (out / "per_shift.tsv").write_text("\n".join(ps) + "\n")
    (out / "verdict.json").write_text(json.dumps(
        {"commit": info["commit"], "rows": rows, "reading": r}, indent=1, sort_keys=True,
        default=str) + "\n")
    print((out / "summary.tsv").read_text())
    print(json.dumps(r, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
