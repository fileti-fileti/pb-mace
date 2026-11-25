"""Tests for scripts/prep_na_q1_check.py (stdlib only)."""
import json
import os
import random
import unittest
from pathlib import Path

from helpers import TempRepo, run  # noqa: F401  (helpers puts scripts/ on sys.path)

import prep_na_translation as pt
import prep_na_q1_check as q

EV_INP = """&GLOBAL
  PROJECT rqz
  RUN_TYPE MD
  PRINT_LEVEL LOW
  SEED 4301
&END GLOBAL
&FORCE_EVAL
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME POTENTIAL
    WFN_RESTART_FILE_NAME {seed}
    &MGRID
      CUTOFF 700
      REL_CUTOFF 70
    &END MGRID
    &QS
      EPS_DEFAULT 1.0E-12
      EXTRAPOLATION USE_GUESS
    &END QS
    &SCF
      SCF_GUESS RESTART
    &END SCF
    &XC
      &vdW_POTENTIAL
        &PAIR_POTENTIAL
          PARAMETER_FILE_NAME dftd3.dat
        &END PAIR_POTENTIAL
      &END vdW_POTENTIAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC 10.087 10.087 36.002
    &END CELL
    &COORD
      @INCLUDE COORD.inc
    &END COORD
    &KIND Fe3
      ELEMENT Fe
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q16
      &DFT_PLUS_U on
        INIT_U_RAMPING_EACH_SCF F
        L 2
        U_MINUS_J [eV] 6.0
        U_RAMPING [eV] 0.0
      &END DFT_PLUS_U
    &END KIND
    &KIND Na
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q9
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
&MOTION
  &MD
    ENSEMBLE REFTRAJ
    STEPS 3
    &REFTRAJ
      TRAJ_FILE_NAME pool_lote.xyz
      FIRST_SNAPSHOT 1
      LAST_SNAPSHOT 3
    &END REFTRAJ
  &END MD
&END MOTION
"""
GEN_INP = EV_INP.replace("  SEED 4301\n", "  SEED 4105\n").replace(
    "    WFN_RESTART_FILE_NAME {seed}\n", "").replace(
    "SCF_GUESS RESTART", "SCF_GUESS ATOMIC").replace(
    "INIT_U_RAMPING_EACH_SCF F", "INIT_U_RAMPING_EACH_SCF T").replace(
    "U_RAMPING [eV] 0.0", "U_RAMPING [eV] 0.5").replace(
    "STEPS 3", "STEPS 8").replace("LAST_SNAPSHOT 3", "LAST_SNAPSHOT 8").replace(
    "&END MD\n", "&END MD\n\n")
BASIS = " Fe DZVP-MOLOPT-SR-GTH DZVP-MOLOPT-SR-GTH-q16\n Na DZVP-MOLOPT-SR-GTH DZVP-MOLOPT-SR-GTH-q9\n"
POT = "Fe GTH-PBE-q16\nNa GTH-PBE-q9 GTH-PBE\n"
COORD = "  Fe3 0.0 0.0 0.0\n  Na 2.5 2.5 2.5\n"
NA_Q1 = {"basis_set": "TZVP-MOLOPT-PBE-GTH-q1", "basis_file": "BASIS_MOLOPT_UZH",
         "potential": "GTH-PBE-q1", "potential_file": "POTENTIAL_UZH"}


def pool(tag):
    return "".join("2\n i = {k}, {t}\nFe {x:.1f} 0.0 0.0\nNa 2.5 2.5 2.5\n".format(
        k=k, t=tag, x=0.1 * k) for k in (1, 2, 3))


def frc(tag):
    return "".join("2\n i = {k}, E = -1 {t}\n Fe 0.0{k} 0.0 0.0\n Na -0.0{k} 0.0 0.0\n".format(
        k=k, t=tag) for k in (1, 2, 3))


def out_text(spin0):
    blk = """                     Mulliken Population Analysis

 #  Atom  Element  Kind  Atomic population (alpha,beta) Net charge  Spin moment
      1     Fe       1         9.9     5.4     0.6     {s:.6f}
      2     Na       2         4.5     4.5     1.0     0.000000
 # Total charge and spin      1.0   1.0    0.0   1.0
  outer SCF loop converged in   2 iterations
 ENERGY| Total FORCE_EVAL ( QS ) energy [a.u.]:            -1552.6
"""
    return "".join(blk.format(s=spin0 + 0.01 * k) for k in (1, 2, 3))


class PrepTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        r, ext = self.t.repo, self.t.ext
        self.legacy = ext / "legacy"
        self.seed = self.legacy / "base" / "chute.wfn"
        self.seed.parent.mkdir(parents=True)
        self.seed.write_text("q9 seed wfn")
        self.dirs = {}
        for key, rel in (("A1", "ev/W/rotulos/j01"), ("A2", "ev/W/rotulos/j02"),
                         ("B1", "ev/N/rotulos/j01"), ("B3", "ev/N/rotulos/j03"),
                         ("B4", "ev/N/rotulos/j04")):
            d = self.legacy / rel
            d.mkdir(parents=True)
            (d / "relabel.inp").write_text(EV_INP.format(seed=self.seed).replace(
                "SEED 4301", "SEED 43{:02d}".format(len(self.dirs))))
            (d / "pool_lote.xyz").write_text(pool(key))
            (d / "rqz-frc-1.xyz").write_text(frc(key))
            (d / "relabel.out").write_text(out_text(4.5 + 0.1 * len(self.dirs)))
            (d / "COORD.inc").write_text(COORD)
            self.dirs[key] = d
        (self.dirs["B3"] / "parcial_123").mkdir()           # a restarted label job
        (self.dirs["B4"] / "relabel.inp").write_text(        # another state protocol
            GEN_INP.replace("EXTRAPOLATION USE_GUESS", "EXTRAPOLATION USE_PREV_WF"))
        g = self.legacy / "rot" / "b01"
        g.mkdir(parents=True)
        (g / "relabel.inp").write_text(GEN_INP)
        (g / "COORD.inc").write_text(COORD)
        self.data = ext / "cp2kdata"
        self.data.mkdir()
        for name, txt in (("BASIS_MOLOPT", BASIS), ("POTENTIAL", POT), ("dftd3.dat", "d3\n"),
                          ("BASIS_MOLOPT_UZH", "Na TZVP-MOLOPT-PBE-GTH-q1 x\n"),
                          ("POTENTIAL_UZH", "Na GTH-PBE-q1 GTH-GGA-q1\n")):
            (self.data / name).write_text(txt)
        rows = [("tA", "train", "ev/W/rotulos/j01", k) for k in (1, 2, 3)]
        rows += [("tA", "valid", "ev/W/rotulos/j02", 1)]
        rows += [("tB", "train", "ev/N/rotulos/j01", k) for k in (1, 2, 3)]
        rows += [("tB", "train", "ev/N/rotulos/j03", 1),
                 ("tB", "train", "ev/N/rotulos/j03/parcial_123", 2),
                 ("tB", "train", "ev/N/rotulos/j04", 1), ("tB", "train", "ev/N/rotulos/j04", 2),
                 ("tC", "train", "ev/W/rotulos/j01", 1)]
        tsv = ["i\tconfig_type\tgrupo\tdestino\torigem\tframe\tpool\tE_eV"]
        tsv += ["{}\t{}\t{}:0\t{}\t{}/relabel.out\t{}\t{}\t-1.5".format(i, ct, ct, dest, o, k, k)
                for i, (ct, dest, o, k) in enumerate(rows, 1)]
        (self.legacy / "consolidado").mkdir()
        (self.legacy / "consolidado" / "frames.tsv").write_text("\n".join(tsv) + "\n")
        (r / "configs").mkdir()
        (r / "configs" / "sums.sha256").write_text("{}  frames.tsv\n".format(
            pt.pm.sha256(self.legacy / "consolidado" / "frames.tsv")))
        self.cfg = {
            "description": "t", "legacy_root": str(self.legacy),
            "frames_tsv": "consolidado/frames.tsv", "frames_tsv_sums": "configs/sums.sha256",
            "cp2k_data_dir": str(self.data),
            "draw": {"seed": 7, "split": "train", "n_per_stratum": 2,
                     "strata": [["A", ["tA"]], ["B", ["tB"]]], "repro_strata": ["B"]},
            "seed_protocol_dir": "rot/b01", "q9_seed": "base/chute.wfn", "na_q1": NA_Q1,
            "forces_file": "rqz-frc-1.xyz", "seed_job_time": "01:00:00",
            "settings": {
                "q9-c700": {"cutoff": 700, "rel_cutoff": 70, "na": "q9", "frames": "repro",
                            "time": "01:00:00"},
                "q1-c2000": {"cutoff": 2000, "rel_cutoff": 70, "na": "q1", "frames": "all",
                             "time": "2-00:00:00"}},
            "slurm": {"partition": "EPYC_9734", "nodelist": "n12", "ntasks": 96,
                      "cpus_per_task": 1, "layout_source": "test"}}
        self.mcfg = {"partitions": ["EPYC_9734"], "modules": {"cp2k": "cp2k/x"}}

    def tearDown(self):
        self.t.__exit__(None, None, None)

    def commit_cfg(self):
        (self.t.repo / "configs" / "t.json").write_text(json.dumps(self.cfg))
        run(["git", "add", "-A"], self.t.repo)
        run(["git", "commit", "-q", "-m", "cfg", "--allow-empty"], self.t.repo)

    def prep(self, name="T"):
        self.commit_cfg()
        return q.prepare(self.t.repo, "configs/t.json", name, machine="neumann", mcfg=self.mcfg)

    def refused(self, msg=None):
        with self.assertRaises(pt.PrepError, msg=msg):
            self.prep(name="R")

    def test_draw_is_seeded_training_side_and_eligible(self):
        rows = q.read_tsv((self.legacy / "consolidado" / "frames.tsv").read_text())
        d = q.draw(rows, self.cfg["draw"], self.legacy, self.seed)
        self.assertEqual(d, q.draw(rows, self.cfg["draw"], self.legacy, self.seed))
        self.assertEqual([s for s, _ in d], ["A", "A", "B", "B"])
        rng = random.Random(7)
        want = rng.sample([r for r in rows if r["i"] in ("1", "2", "3")], 2)
        want += rng.sample([r for r in rows if r["i"] in ("5", "6", "7")], 2)  # not j03, j04
        self.assertEqual([r["i"] for _, r in d], [r["i"] for r in want])
        cache = {}
        self.assertFalse(q.eligible("ev/N/rotulos/j04/relabel.out", self.legacy, self.seed, cache))
        self.assertFalse(q.eligible("ev/N/rotulos/j03/relabel.out", self.legacy, self.seed, cache))
        self.assertTrue(q.eligible("ev/N/rotulos/j01/relabel.out", self.legacy, self.seed, cache))
        self.cfg["draw"]["n_per_stratum"] = 4                   # only 3 eligible per stratum
        with self.assertRaises(pt.PrepError):
            q.draw(rows, self.cfg["draw"], self.legacy, self.seed)

    def test_run_dirs(self):
        out, cmds = self.prep()
        self.assertEqual(len(cmds), 3)
        self.assertTrue(cmds[0].endswith("q1-seed && sbatch job.sh"))
        info = json.loads((out / "run_info.json").read_text())
        fr = info["frames"]
        self.assertEqual([f["id"] for f in fr], ["f01", "f02", "f03", "f04"])
        self.assertEqual(info["repro_frames"], ["f03"])            # first drawn of stratum B
        self.assertEqual(info["settings"]["q9-c700"]["frames"], ["f03"])
        self.assertEqual(info["settings"]["q1-c2000"]["frames"], ["f01", "f02", "f03", "f04"])
        f1 = fr[0]
        spin0 = 4.5 + 0.1 * (0 if "j01" in f1["origem"] else 1)
        self.assertAlmostEqual(f1["legacy_fe_spins"]["1"], spin0 + 0.01 * f1["snapshot"])
        self.assertEqual((out / "seed_q9.wfn").read_text(), "q9 seed wfn")
        # seed generation: atomic guess with the U ramp, Na q1 at 700/70, one snapshot of f01
        g = (out / "q1-seed" / "seed_gen" / "relabel.inp").read_text()
        for key, val in (("SCF_GUESS", "ATOMIC"), ("U_RAMPING", "[eV] 0.5"),
                         ("INIT_U_RAMPING_EACH_SCF", "T"), ("CUTOFF", "700"),
                         ("TRAJ_FILE_NAME", "pool.xyz"), ("LAST_SNAPSHOT", "1"), ("STEPS", "1")):
            self.assertEqual(pt.kw_values(g, key), [val], key)
        self.assertEqual(pt.kinds(g)["Na"]["potential"], "GTH-PBE-q1")
        self.assertEqual(pt.kw_values(g, "WFN_RESTART_FILE_NAME"), [])
        sp = pt.read_xyz_frame((out / "q1-seed" / "seed_gen" / "pool.xyz").read_text(), 1, "p")[2]
        self.assertAlmostEqual(sp[0][1], 0.1 * f1["snapshot"])
        seedjob = (out / "q1-seed" / "job.sh").read_text()
        self.assertIn("cp2k_in seed_gen", seedjob)
        self.assertIn("cp seed_gen/rqz-RESTART.wfn seed.wfn", seedjob)
        # settings: only CUTOFF/REL_CUTOFF, Na, seed file and the one snapshot change
        rd = out / "q1-c2000"
        inp = (rd / "relabel.inp").read_text()
        for key, val in (("CUTOFF", "2000"), ("REL_CUTOFF", "70"), ("SCF_GUESS", "RESTART"),
                         ("U_RAMPING", "[eV] 0.0"), ("INIT_U_RAMPING_EACH_SCF", "F"),
                         ("WFN_RESTART_FILE_NAME", "seed.wfn"), ("EXTRAPOLATION", "USE_GUESS"),
                         ("LAST_SNAPSHOT", "1")):
            self.assertEqual(pt.kw_values(inp, key), [val], key)
        self.assertEqual(pt.kinds(inp)["Na"]["basis"], "TZVP-MOLOPT-PBE-GTH-q1")
        self.assertEqual(os.readlink(str(rd / "seed.wfn")), "../q1-seed/seed.wfn")
        self.assertEqual(os.readlink(str(out / "q9-c700" / "seed.wfn")), "../seed_q9.wfn")
        self.assertEqual(pt.kw_values((out / "q9-c700" / "relabel.inp").read_text(), "CUTOFF"),
                         ["700"])
        for fn in ("COORD.inc", "BASIS_MOLOPT", "POTENTIAL", "dftd3.dat", "BASIS_MOLOPT_UZH",
                   "POTENTIAL_UZH"):
            self.assertTrue((rd / fn).is_file(), fn)
        d4 = rd / "f04"
        self.assertEqual((d4 / "relabel.inp").read_text(), inp)
        self.assertEqual(os.readlink(str(d4 / "seed.wfn")), "../seed.wfn")
        f4 = fr[3]
        a = pt.read_xyz_frame((d4 / "pool.xyz").read_text(), 1, "p")[2]
        self.assertAlmostEqual(a[0][1], 0.1 * f4["snapshot"])
        ref = pt.read_forces((d4 / "ref_frc.xyz").read_text(), 1, "r")
        self.assertAlmostEqual(ref[0][1], 0.01 * f4["snapshot"])
        job = (rd / "job.sh").read_text()
        for s in ("for d in f01 f02 f03 f04; do cp2k_in $d; done", "#SBATCH -n 96\n",
                  "#SBATCH --cpus-per-task=1\n", "#SBATCH -w n12\n", "#SBATCH --time=2-00:00:00\n",
                  "module load cp2k/x", '[ -s "$RUNDIR/seed.wfn" ]'):
            self.assertIn(s, job)
        self.assertIn("for d in f03; do", (out / "q9-c700" / "job.sh").read_text())

    def test_refusals(self):
        # a drawn origem whose input differs beyond SEED/STEPS/LAST_SNAPSHOT
        p = self.dirs["B1"] / "relabel.inp"
        good = p.read_text()
        p.write_text(good.replace("EPS_DEFAULT 1.0E-12", "EPS_DEFAULT 1.0E-10"))
        self.refused("origem input differs")
        p.write_text(good)
        # seed protocol differs beyond the state lines
        g = self.legacy / "rot" / "b01" / "relabel.inp"
        g.write_text(GEN_INP.replace("CUTOFF 700", "CUTOFF 600"))
        self.refused("seed protocol differs")
        g.write_text(GEN_INP)
        # the base input's seed is not the configured q9 seed
        self.cfg["q9_seed"] = "base/other.wfn"
        (self.legacy / "base" / "other.wfn").write_text("x")
        self.refused("q9 seed")
        self.cfg["q9_seed"] = "base/chute.wfn"
        # bad config values
        self.cfg["draw"]["split"] = "test"
        self.refused("test split")
        self.cfg["draw"]["split"] = "train"
        self.cfg["settings"]["q9-c700"]["na"] = "q3"
        self.refused("na")
        self.cfg["settings"]["q9-c700"]["na"] = "q9"
        # frames.tsv checksum
        (self.t.repo / "configs" / "sums.sha256").write_text("0" * 64 + "  frames.tsv\n")
        self.refused("checksum")

    def test_existing_dir_and_dirty_tree_refused(self):
        self.prep(name="A")
        with self.assertRaises(pt.PrepError):
            q.prepare(self.t.repo, "configs/t.json", "A", machine="neumann", mcfg=self.mcfg)
        (self.t.repo / "configs" / "dirty.txt").write_text("x")
        with self.assertRaises(pt.PrepError):
            q.prepare(self.t.repo, "configs/t.json", "B", machine="neumann", mcfg=self.mcfg)


if __name__ == "__main__":
    unittest.main()
