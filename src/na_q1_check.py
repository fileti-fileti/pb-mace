#!/usr/bin/env python3
"""Analysis of the q1 check of the Na relabelling protocol (docs/na-relabel.md, ADR-0016).

Usage: python3 src/na_q1_check.py RUN_DIR
RUN_DIR: written by scripts/prep_na_q1_check.py (run_info.json, q1-seed/, one dir per
setting with one dir per frame). Writes RUN_DIR/analysis/{frames.tsv, forces.tsv,
verdict.json} and prints the verdict.

Reading rule (fixed 2026-11-25 in docs/na-relabel.md, before any input was prepared):
- Valid frame: in each of q9-c2000, q1-c700 and q1-c2000 the single point ended with a
  converged SCF and every Fe Mulliken spin is within 0.01 of the frame's legacy label.
  Fewer than 9 valid frames -> inconclusive.
- Checks (a failure makes the test inconclusive): the q1 seed (q1-seed/seed_gen) ended,
  converged and has every Fe spin within 0.01 of its frame's legacy label; every q9-c700
  frame ended, converged and reproduces its legacy forces within max |dF| <= 10 meV/A.
- Metric: dE_i^s = E_i^s - mean over the valid frames of E^s; D(A, B) = max over the valid
  frames of |dE_i^A - dE_i^B| (meV); kT = 25.9 meV (300 K).
- yes: D(q1-c700, q9-c2000) <= kT. no: otherwise, if D(q1-c2000, q9-c2000) > 2 kT.
  inconclusive: otherwise.
- Reported only: D(q1-c700, q1-c2000); D per stratum (dE relative to the stratum's valid
  frames); RMS and max |dF| per element for the three pairs over the valid frames; |SF|
  per frame and setting; Fe spin differences; SCF steps (OT lines) and CP2K wall time.
Standard library only; runs on Python >= 3.6.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import na_translation as nt  # noqa: E402  (parse_out, read_single, max_dspin, units)
import prep_na_translation as pt  # noqa: E402  (force reader)

SPIN_TOL = 0.01
MIN_VALID = 9
REPRO_TOL = 10.0          # meV/A
KT_MEV = 25.9             # 300 K
REPRO = "q9-c700"
REF, PROTO, CTRL = "q9-c2000", "q1-c700", "q1-c2000"
VALID_SETTINGS = (REF, PROTO, CTRL)
PAIRS = ((PROTO, REF), (CTRL, REF), (PROTO, CTRL))
OT_RE = re.compile(r"^\s+\d+\s+OT\s", re.M)
TIME_RE = re.compile(r"^\s*CP2K\s+1\s+1\.0\s+\S+\s+\S+\s+\S+\s+(\S+)\s*$", re.M)


def read_point(sd, forces_file):
    """-> {"step", "forces", "scf_steps", "time_s"}; step/forces None unless ended with one step."""
    st, f, _ = nt.read_single(sd, forces_file)
    out = sd / "relabel.out"
    text = out.read_text() if out.is_file() else ""
    t = TIME_RE.findall(text)
    return {"step": st, "forces": f, "scf_steps": len(OT_RE.findall(text)),
            "time_s": float(t[-1]) if t else None}


def point_ok(p, ref_spins):
    """-> (ok, max Fe spin difference or None)."""
    if p is None or p["step"] is None or not p["step"]["converged"]:
        return False, None
    d = nt.max_dspin(p["step"]["fe_spins"], ref_spins)
    return d <= SPIN_TOL, d


def sum_force(forces):
    return math.sqrt(sum(sum(a[c] for a in forces) ** 2 for c in (1, 2, 3))) * nt.TO_MEV_A


def rel_energies(E, ids):
    """E: {id: energy meV} -> {id: E - mean over ids}."""
    mu = sum(E[i] for i in ids) / len(ids)
    return {i: E[i] - mu for i in ids}


def dmax(EA, EB, ids):
    if not ids:
        return None
    a, b = rel_energies(EA, ids), rel_energies(EB, ids)
    return max(abs(a[i] - b[i]) for i in ids)


def force_pair_stats(pts, a, b, ids):
    """Pooled over the frames ids: {el: {"n", "rms", "max"}} of the force difference (meV/A)."""
    acc = {}
    for i in ids:
        for x, y in zip(pts[(a, i)]["forces"], pts[(b, i)]["forces"]):
            if x[0] != y[0]:
                raise ValueError("element order differs")
            s, m, n = acc.get(x[0], (0.0, 0.0, 0))
            d = [(x[c] - y[c]) * nt.TO_MEV_A for c in (1, 2, 3)]
            acc[x[0]] = (s + sum(v * v for v in d), max([m] + [abs(v) for v in d]), n + 3)
    return {el: {"n": n, "rms": math.sqrt(s / n), "max": m} for el, (s, m, n) in acc.items()}


def reading(info, pts, seed, refs):
    """pts: {(setting, id): point}; seed: point of q1-seed/seed_gen; refs: {id: forces}."""
    frames = info["frames"]
    legacy = {f["id"]: f["legacy_fe_spins"] for f in frames}
    checks = {}
    ok, d = point_ok(seed, legacy[info["seed_frame"]])
    checks["q1_seed"] = {"ok": ok, "max_dspin": d}
    rep = {}
    for i in info["settings"][REPRO]["frames"]:
        p = pts.get((REPRO, i))
        if p is None or p["step"] is None or not p["step"]["converged"]:
            rep[i] = None
        else:
            rep[i] = nt.max_abs_diff(p["forces"], refs[i])
    checks["repro_max_dF"] = rep
    checks["repro_ok"] = bool(rep) and all(v is not None and v <= REPRO_TOL for v in rep.values())

    dspin, valid = {}, []
    for f in frames:
        i, good = f["id"], True
        for s in VALID_SETTINGS:
            ok, d = point_ok(pts.get((s, i)), legacy[i])
            dspin["{}|{}".format(s, i)] = d
            good = good and ok
        if good:
            valid.append(i)
    E = {s: {i: pts[(s, i)]["step"]["energy"] * nt.HA_TO_MEV for i in valid}
         for s in VALID_SETTINGS}
    D = {"{}_vs_{}".format(a, b): dmax(E[a], E[b], valid) for a, b in PAIRS}
    d_total, d_pseudo = D["{}_vs_{}".format(PROTO, REF)], D["{}_vs_{}".format(CTRL, REF)]
    if not (checks["q1_seed"]["ok"] and checks["repro_ok"]):
        verdict, why = "inconclusive", "a check failed"
    elif len(valid) < MIN_VALID:
        verdict, why = "inconclusive", "{} valid frames < {}".format(len(valid), MIN_VALID)
    elif d_total <= KT_MEV:
        verdict, why = "yes", "D(q1-c700, q9-c2000) <= kT"
    elif d_pseudo > 2 * KT_MEV:
        verdict, why = "no", "D(q1-c2000, q9-c2000) > 2 kT"
    else:
        verdict, why = "inconclusive", "kT < D(q1-c700, q9-c2000) and D(q1-c2000, q9-c2000) <= 2 kT"
    strata = {}
    for name in sorted({f["stratum"] for f in frames}):
        ids = [f["id"] for f in frames if f["stratum"] == name and f["id"] in valid]
        strata[name] = {"n_valid": len(ids)}
        strata[name].update({"{}_vs_{}".format(a, b): dmax(E[a], E[b], ids) for a, b in PAIRS})
    forces = {"{}_vs_{}".format(a, b): force_pair_stats(pts, a, b, valid) if valid else {}
              for a, b in PAIRS}
    return {"verdict": verdict, "why": why, "kT_meV": KT_MEV, "n_valid": len(valid),
            "n_frames": len(frames), "valid": valid, "D_meV": D, "strata": strata,
            "checks": checks, "forces_meV_A": forces, "max_dspin": dspin}


def load(run_dir):
    info = json.loads((run_dir / "run_info.json").read_text())
    ff = info["forces_file"]
    pts, refs = {}, {}
    for s, si in info["settings"].items():
        for i in si["frames"]:
            sd = run_dir / s / i
            pts[(s, i)] = read_point(sd, ff)
            refs[i] = pt.read_forces((sd / "ref_frc.xyz").read_text(), 1, str(sd / "ref_frc.xyz"))
    seed = read_point(run_dir / "q1-seed" / "seed_gen", ff)
    return info, pts, seed, refs


def fmt(x, nd=1):
    return "" if x is None else "{:.{}f}".format(x, nd)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    info, pts, seed, refs = load(run_dir)
    r = reading(info, pts, seed, refs)
    valid = set(r["valid"])
    rel = {}
    for s in VALID_SETTINGS:
        E = {i: pts[(s, i)]["step"]["energy"] * nt.HA_TO_MEV for i in valid}
        rel[s] = rel_energies(E, sorted(valid)) if valid else {}
    rows = ["id\tstratum\ti\tconfig_type\tsetting\tended\tconverged\tmax_dspin\tvalid_frame\t"
            "E_Ha\tdE_meV\tsumF_meV_A\tscf_steps\ttime_s"]
    for f in info["frames"]:
        for s, si in info["settings"].items():
            if f["id"] not in si["frames"]:
                continue
            p = pts[(s, f["id"])]
            st = p["step"]
            d = r["max_dspin"].get("{}|{}".format(s, f["id"]))
            rows.append("\t".join([
                f["id"], f["stratum"], str(f["i"]), f["config_type"], s, str(st is not None),
                str(bool(st and st["converged"])), fmt(d, 4), str(f["id"] in valid),
                "{:.10f}".format(st["energy"]) if st else "",
                fmt(rel.get(s, {}).get(f["id"]), 2), fmt(sum_force(p["forces"]) if p["forces"] else None),
                str(p["scf_steps"]), fmt(p["time_s"])]))
    out = run_dir / "analysis"
    out.mkdir(exist_ok=True)
    (out / "frames.tsv").write_text("\n".join(rows) + "\n")
    frows = ["pair\telement\tn\trms_meV_A\tmax_meV_A"]
    for pair, els in sorted(r["forces_meV_A"].items()):
        for el, v in sorted(els.items()):
            frows.append("{}\t{}\t{}\t{:.1f}\t{:.1f}".format(pair, el, v["n"], v["rms"], v["max"]))
    (out / "forces.tsv").write_text("\n".join(frows) + "\n")
    (out / "verdict.json").write_text(json.dumps(
        {"commit": info["commit"], "reading": r}, indent=1, sort_keys=True) + "\n")
    print((out / "frames.tsv").read_text())
    print((out / "forces.tsv").read_text())
    print(json.dumps({k: r[k] for k in ("verdict", "why", "n_valid", "D_meV", "strata", "checks")},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
