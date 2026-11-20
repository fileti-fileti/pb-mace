"""Tests for scripts/prep_na_translation.py (stdlib only)."""
import json
import unittest
from pathlib import Path

from helpers import TempRepo, run  # noqa: F401  (helpers puts scripts/ on sys.path)

import prep_na_translation as pt

BASE_INP = """&GLOBAL
  PROJECT rqz
  RUN_TYPE MD
  PRINT_LEVEL LOW
&END GLOBAL
&FORCE_EVAL
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME POTENTIAL
    &MGRID
      CUTOFF 700
      REL_CUTOFF 70
    &END MGRID
    &QS
      EPS_DEFAULT 1.0E-12
      EXTRAPOLATION USE_GUESS
    &END QS
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
      ABC 10.170 10.170 10.170
    &END CELL
    &COORD
      @INCLUDE COORD.inc
    &END COORD
    &KIND Fe2
      ELEMENT Fe
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q16
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
    STEPS 15
    &REFTRAJ
      TRAJ_FILE_NAME pool_lote.xyz
      FIRST_SNAPSHOT 1
      LAST_SNAPSHOT 15
    &END REFTRAJ
  &END MD
&END MOTION
"""
BASIS = (" Fe DZVP-MOLOPT-SR-GTH DZVP-MOLOPT-SR-GTH-q16\n"
         " Na DZVP-MOLOPT-SR-GTH DZVP-MOLOPT-SR-GTH-q9\n")
BASIS_UZH = "Na TZVP-MOLOPT-PBE-GTH-q1 TZVP-MOLOPT-GGA-GTH-q1\n"
POT = "Fe GTH-PBE-q16\nNa GTH-PBE-q9 GTH-PBE\n"
POT_UZH = "Na GTH-PBE-q1 GTH-GGA-q1\n"
COORD = "  Fe2 0.0 0.0 0.0\n  Na 2.5 2.5 2.5\n"
POOL = ("2\n i = 1, frame a\nFe 0.0 0.0 0.0\nNa 2.5 2.5 2.5\n"
        "2\n i = 2, frame b\nFe 0.1 0.0 0.0\nNa 2.6 2.5 2.5\n")
FRC_XYZ = ("2\n i = 1, E = -1\n Fe 0.01 0.02 0.03\n Na -0.01 -0.02 -0.03\n"
           "2\n i = 2, E = -1\n Fe 0.11 0.12 0.13\n Na -0.11 -0.12 -0.13\n")
FRC_TABLE = """ ATOMIC FORCES in [a.u.]

 # Atom   Kind   Element          X              Y              Z
      1      1      Fe          0.01000000     0.02000000     0.03000000
      2      2      Na         -0.01000000    -0.02000000    -0.03000000
 SUM OF ATOMIC FORCES           0.00000000     0.00000000     0.00000000     0.00000000

 ATOMIC FORCES in [a.u.]

 # Atom   Kind   Element          X              Y              Z
      1      1      Fe          0.11000000     0.12000000     0.13000000
      2      2      Na         -0.11000000    -0.12000000    -0.13000000
 SUM OF ATOMIC FORCES           0.00000000     0.00000000     0.00000000     0.00000000
"""
NA_Q1 = {"basis_set": "TZVP-MOLOPT-PBE-GTH-q1", "basis_file": "BASIS_MOLOPT_UZH",
         "potential": "GTH-PBE-q1", "potential_file": "POTENTIAL_UZH"}


class GridTest(unittest.TestCase):
    def test_grid_sizes_of_the_2026_11_19_fit(self):
        # 700 Ry: 162 (10.170 A), 324 (20.340 A), 576 (36.002 A); 400 Ry: 125, 450.
        self.assertEqual(pt.grid_points(10.170, 700), 162)
        self.assertEqual(pt.grid_points(20.340, 700), 324)
        self.assertEqual(pt.grid_points(36.002, 700), 576)
        self.assertEqual(pt.grid_points(10.170, 400), 125)
        self.assertEqual(pt.grid_points(10.087, 400), 125)
        self.assertEqual(pt.grid_points(36.002, 400), 450)

    def test_smooth_and_monotonic(self):
        last = 0
        for e in (400, 700, 1200, 1600):
            n = pt.grid_points(10.170, e)
            self.assertTrue(pt._smooth(n))
            self.assertGreater(n, last)
            last = n


class XyzTest(unittest.TestCase):
    def test_read_frame_and_shift(self):
        n, comment, atoms = pt.read_xyz_frame(POOL, 2, "pool")
        self.assertEqual((n, comment.strip()), (2, "i = 2, frame b"))
        self.assertEqual(atoms[0], ("Fe", 0.1, 0.0, 0.0))
        s = pt.shifted(atoms, 0.25)
        self.assertAlmostEqual(s[1][1] - atoms[1][1], 0.25)
        self.assertEqual(s[1][2:], atoms[1][2:])
        with self.assertRaises(pt.PrepError):
            pt.read_xyz_frame(POOL, 3, "pool")

    def test_write_read_roundtrip(self):
        txt = pt.write_xyz([("c0", [("Na", 1.0, 2.0, 3.0)]), ("c1", [("Na", 1.5, 2.0, 3.0)])])
        self.assertEqual(pt.read_xyz_frame(txt, 2, "t")[2], [("Na", 1.5, 2.0, 3.0)])

    def test_both_force_formats(self):
        for txt in (FRC_XYZ, FRC_TABLE):
            f = pt.read_forces(txt, 2, "f")
            self.assertEqual([a[0] for a in f], ["Fe", "Na"])
            self.assertEqual(f[1][1:], (-0.11, -0.12, -0.13))
        with self.assertRaises(pt.PrepError):
            pt.read_forces(FRC_TABLE, 3, "f")


class InputTest(unittest.TestCase):
    def test_set_kw_exactly_one_and_old_value(self):
        t = pt.set_kw(BASE_INP, "CUTOFF", 1600, old="700")
        self.assertEqual(pt.kw_values(t, "CUTOFF"), ["1600"])
        self.assertEqual(pt.kw_values(t, "REL_CUTOFF"), ["70"])   # not touched
        with self.assertRaises(pt.PrepError):
            pt.set_kw(BASE_INP, "CUTOFF", 1600, old="400")
        with self.assertRaises(pt.PrepError):
            pt.set_kw(BASE_INP + "  CUTOFF 5\n", "CUTOFF", 1)
        with self.assertRaises(pt.PrepError):
            pt.set_kw(BASE_INP, "NO_SUCH_KEY", 1)

    def test_build_input(self):
        t = pt.build_input(BASE_INP, {"cutoff": 400, "rel_cutoff": 60}, 4)
        for key, val in (("PRINT_LEVEL", "MEDIUM"), ("CUTOFF", "400"), ("REL_CUTOFF", "60"),
                         ("EXTRAPOLATION", "USE_PREV_WF"), ("TRAJ_FILE_NAME", "pool.xyz"),
                         ("FIRST_SNAPSHOT", "1"), ("LAST_SNAPSHOT", "4"), ("STEPS", "4")):
            self.assertEqual(pt.kw_values(t, key), [val], key)
        self.assertEqual(pt.kinds(t)["Na"]["potential"], "GTH-PBE-q9")
        with self.assertRaises(pt.PrepError):   # not the qz protocol
            pt.build_input(t, {"cutoff": 700, "rel_cutoff": 70}, 4)

    def test_swap_na_only_touches_na(self):
        t = pt.build_input(BASE_INP, {"cutoff": 700, "rel_cutoff": 70, "na": NA_Q1}, 4)
        k = pt.kinds(t)
        self.assertEqual(k["Na"], {"element": "Na", "basis": "TZVP-MOLOPT-PBE-GTH-q1",
                                   "potential": "GTH-PBE-q1", "potential_file": "POTENTIAL_UZH"})
        self.assertEqual(k["Fe2"], {"element": "Fe", "basis": "DZVP-MOLOPT-SR-GTH",
                                    "potential": "GTH-PBE-q16"})
        self.assertEqual(pt.kw_values(t, "BASIS_SET_FILE_NAME"), ["BASIS_MOLOPT", "BASIS_MOLOPT_UZH"])
        pt.check_kinds(t, {"BASIS_MOLOPT": BASIS, "BASIS_MOLOPT_UZH": BASIS_UZH,
                           "POTENTIAL": POT, "POTENTIAL_UZH": POT_UZH})
        with self.assertRaises(pt.PrepError):   # q1 basis missing from the files
            pt.check_kinds(t, {"BASIS_MOLOPT": BASIS, "BASIS_MOLOPT_UZH": "",
                               "POTENTIAL": POT, "POTENTIAL_UZH": POT_UZH})

    def test_include_elements(self):
        self.assertEqual(pt.include_elements(COORD, pt.kinds(BASE_INP)), ["Fe", "Na"])


class PrepareTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        r, ext = self.t.repo, self.t.ext
        self.legacy = ext / "legacy"
        d = self.legacy / "sysA" / "b01"
        d.mkdir(parents=True)
        (d / "relabel.inp").write_text(BASE_INP)
        (d / "pool_lote.xyz").write_text(POOL)
        (d / "rqz-frc-1.xyz").write_text(FRC_XYZ)
        (d / "COORD.inc").write_text(COORD)
        (d / "BASIS_MOLOPT").write_text(BASIS)
        self.data = ext / "cp2kdata"
        self.data.mkdir()
        for name, txt in (("POTENTIAL", POT), ("dftd3.dat", "d3\n"),
                          ("BASIS_MOLOPT_UZH", BASIS_UZH), ("POTENTIAL_UZH", POT_UZH)):
            (self.data / name).write_text(txt)
        (self.legacy / "consolidado").mkdir()
        self.tsv = ("i\tconfig_type\tgrupo\tdestino\torigem\tframe\tpool\tE_eV\n"
                    "1\tA\tA:0\ttrain\tsysA/b01/relabel.out\t2\t2\t-1\n"
                    "2\tA\tA:0\ttest\tsysA/b01/relabel.out\t1\t1\t-1\n")
        (self.legacy / "consolidado" / "frames.tsv").write_text(self.tsv)
        (r / "data").mkdir()
        self.write_sums()
        self.cfg = {
            "description": "t", "legacy_root": str(self.legacy),
            "frames_tsv": "consolidado/frames.tsv", "frames_tsv_sums": "configs/sums.sha256",
            "cp2k_data_dir": str(self.data), "n_shifts": 4,
            "frames": {"a": {"dir": "sysA/b01", "snapshot": 2, "forces_file": "rqz-frc-1.xyz",
                             "natoms": 2, "cell": 10.170}},
            "settings": {"c700": {"cutoff": 700, "rel_cutoff": 70},
                         "q1": {"cutoff": 700, "rel_cutoff": 70, "na": NA_Q1}},
            "runs": [["a", "c700", "01:00:00"], ["a", "q1", "01:00:00"]],
            "slurm": {"partition": "EPYC_9734", "nodelist": "n12", "ntasks": 28,
                      "cpus_per_task": 2, "layout_source": "test"}}
        self.mcfg = {"partitions": ["batch", "EPYC_9734"], "modules": {"cp2k": "cp2k/x"}}

    def tearDown(self):
        self.t.__exit__(None, None, None)

    def write_sums(self, digest=None):
        tsv = self.legacy / "consolidado" / "frames.tsv"
        (self.t.repo / "configs").mkdir(exist_ok=True)
        (self.t.repo / "configs" / "sums.sha256").write_text(
            "{}  frames.tsv\n".format(digest or pt.pm.sha256(tsv)))

    def commit_cfg(self, cfg=None):
        p = self.t.repo / "configs" / "t.json"
        p.write_text(json.dumps(cfg or self.cfg))
        run(["git", "add", "-A"], self.t.repo)
        run(["git", "commit", "-q", "-m", "cfg"], self.t.repo)
        return p

    def prep(self, name="T"):
        return pt.prepare(self.t.repo, "configs/t.json", name, machine="neumann", mcfg=self.mcfg)

    def test_run_dirs(self):
        self.commit_cfg()
        out, cmds = self.prep()
        self.assertEqual(len(cmds), 2)
        rd = out / "a-c700"
        n, h = pt.grid_points(10.170, 700), 10.170 / 162
        self.assertEqual(n, 162)
        pool = (rd / "pool.xyz").read_text()
        for k in range(4):
            a = pt.read_xyz_frame(pool, k + 1, "pool")[2]
            self.assertAlmostEqual(a[1][1], 2.6 + k * h / 4, places=9)
            self.assertEqual(a[1][2:], (2.5, 2.5))
        self.assertEqual(pt.read_forces((rd / "ref_frc.xyz").read_text(), 1, "r")[1][1:],
                         (-0.11, -0.12, -0.13))
        inp = (rd / "relabel.inp").read_text()
        self.assertEqual(pt.kw_values(inp, "LAST_SNAPSHOT"), ["4"])
        for f in ("COORD.inc", "BASIS_MOLOPT", "POTENTIAL", "dftd3.dat", "job.sh"):
            self.assertTrue((rd / f).is_file(), f)
        self.assertTrue((out / "a-q1" / "POTENTIAL_UZH").is_file())
        job = (rd / "job.sh").read_text()
        self.assertIn("#SBATCH -n 28", job)
        self.assertIn("module load cp2k/x", job)
        info = json.loads((out / "run_info.json").read_text())
        head = run(["git", "rev-parse", "HEAD"], self.t.repo).stdout.strip()
        self.assertEqual(info["commit"], head)
        self.assertEqual(info["runs"]["a-c700"]["grid_n_expected"], 162)
        self.assertEqual(info["runs"]["a-c700"]["split"], "train")
        self.assertEqual(info["runs"]["a-q1"]["files"]["POTENTIAL_UZH"]["source"],
                         str((self.data / "POTENTIAL_UZH").resolve()))

    def test_refusals(self):
        self.commit_cfg()
        self.prep()
        with self.assertRaises(pt.PrepError):           # run dir exists
            self.prep()
        (self.t.repo / "configs" / "x.txt").write_text("dirty")
        with self.assertRaises(pt.PrepError):           # dirty tree
            self.prep("U")

    def test_test_frame_refused(self):
        cfg = dict(self.cfg)
        cfg["frames"] = {"a": dict(self.cfg["frames"]["a"], snapshot=1)}
        self.commit_cfg(cfg)
        with self.assertRaises(pt.PrepError) as cm:
            self.prep()
        self.assertIn("'test'", str(cm.exception))

    def test_data_checks(self):
        self.write_sums("0" * 64)
        self.commit_cfg()
        with self.assertRaises(pt.PrepError):           # frames.tsv checksum
            self.prep()
        self.write_sums()
        cfg = dict(self.cfg)
        cfg["frames"] = {"a": dict(self.cfg["frames"]["a"], natoms=3)}
        self.commit_cfg(cfg)
        with self.assertRaises(pt.PrepError):           # atom count
            self.prep("V")
        cfg["frames"] = {"a": dict(self.cfg["frames"]["a"], cell=9.9)}
        self.commit_cfg(cfg)
        with self.assertRaises(pt.PrepError):           # cell
            self.prep("W")

    def test_config_checks(self):
        cfg = dict(self.cfg, extra=1)
        self.commit_cfg(cfg)
        with self.assertRaises(pt.PrepError):
            self.prep()
        cfg = dict(self.cfg, runs=[["a", "nope", "01:00:00"]])
        self.commit_cfg(cfg)
        with self.assertRaises(pt.PrepError):
            self.prep()
        cfg = dict(self.cfg, slurm=dict(self.cfg["slurm"], partition="gpu"))
        self.commit_cfg(cfg)
        with self.assertRaises(pt.PrepError):
            self.prep()


if __name__ == "__main__":
    unittest.main()
