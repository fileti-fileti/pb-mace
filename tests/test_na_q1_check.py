"""Tests for src/na_q1_check.py (stdlib only): the reading rule of docs/na-relabel.md."""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("na_q1_check", str(ROOT / "src" / "na_q1_check.py"))
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

HA = 27211.386245988          # meV per Ha
IDS = ["f{:02d}".format(k) for k in range(1, 13)]
STRATA = ["EQ"] * 3 + ["N3"] * 3 + ["W4"] * 3 + ["TS"] * 3
LEGACY_SPIN = 4.5             # Fe 1: high spin
LEGACY_LS = 0.3               # Fe 3: low spin


def out_text(e_ha, spin, converged=True, ended=True, ls=LEGACY_LS, total=1.0):
    s = """                     Mulliken Population Analysis

 #  Atom  Element  Kind  Atomic population (alpha,beta) Net charge  Spin moment
      1     Fe       1         9.9     5.4     0.6     {spin:.6f}
      2     Na       2         4.5     4.5     1.0     0.000000
      3     Fe       1         7.9     7.6     0.5     {ls:.6f}
 # Total charge and spin      1.0   1.0    0.0   {total:.6f}
     1 OT DIIS     0.50E-01    1.5     0.00000060     -1364.6928087289 -1.36E+03
     2 OT DIIS     0.50E-01    1.5     0.00000060     -1364.6928087289 -1.36E+03
  {status}
 ENERGY| Total FORCE_EVAL ( QS ) energy [a.u.]:            {e:.12f}
 CP2K                                 1  1.0    0.012    0.031  364.297  364.298
""".format(spin=spin, ls=ls, total=total, e=e_ha, status="outer SCF loop converged in   2 iterations" if converged
           else "SCF run NOT converged")
    return s + (" **** PROGRAM ENDED ****\n" if ended else "")


INP = "&FORCE_EVAL\n  &DFT\n    UKS\n    MULTIPLICITY 2\n  &END DFT\n&END FORCE_EVAL\n"


def frc(fx):
    return "2\n i = 1, E = -1\n Fe {:.8f} 0.0 0.0\n Na {:.8f} 0.0 0.0\n".format(fx, -fx)


class Run(object):
    """A synthetic run dir. Energies in meV relative to a base; forces in Ha/bohr."""

    def __init__(self, root):
        self.root = Path(root)
        self.base = {i: -3950.0 + 0.01 * k for k, i in enumerate(IDS)}     # Ha
        self.delta = {s: {i: 0.0 for i in IDS} for s in ("q9-c2000", "q1-c700", "q1-c2000")}
        self.offset = {"q9-c2000": 0.0, "q1-c700": 1.0, "q1-c2000": 1.5}   # Ha, constant
        self.spin = {}                                                       # (s, id) -> spin
        self.ls = {}                                                         # (s, id) -> Fe 3 spin
        self.total = {}                                                      # (s, id) -> total spin
        self.unconv = set()
        self.seed_spin = LEGACY_SPIN
        self.seed_ls = LEGACY_LS
        self.seed_total = 1.0
        self.repro_fx = 0.01

    def write(self):
        settings = {"q9-c700": {"frames": ["f01", "f10"]}}
        settings.update({s: {"frames": list(IDS)} for s in self.delta})
        info = {"commit": "abc", "forces_file": "rqz-frc-1.xyz", "seed_frame": "f01",
                "frames": [{"id": i, "stratum": st, "i": k, "config_type": "t",
                            "legacy_fe_spins": {"1": LEGACY_SPIN, "3": LEGACY_LS}}
                           for k, (i, st) in enumerate(zip(IDS, STRATA))],
                "settings": settings}
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "run_info.json").write_text(json.dumps(info))
        for s, si in settings.items():
            for i in si["frames"]:
                d = self.root / s / i
                d.mkdir(parents=True, exist_ok=True)
                (d / "relabel.inp").write_text(INP)
                (d / "ref_frc.xyz").write_text(frc(0.01))
                if s == "q9-c700":
                    e, fx = self.base[i], self.repro_fx
                else:
                    e = self.base[i] + self.offset[s] + self.delta[s][i] / HA
                    fx = 0.01 + (0.001 if s.startswith("q1") else 0.0)
                (d / "relabel.out").write_text(out_text(
                    e, self.spin.get((s, i), LEGACY_SPIN), converged=(s, i) not in self.unconv,
                    ls=self.ls.get((s, i), LEGACY_LS), total=self.total.get((s, i), 1.0)))
                (d / "rqz-frc-1.xyz").write_text(frc(fx))
        sd = self.root / "q1-seed" / "seed_gen"
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "relabel.inp").write_text(INP)
        (sd / "relabel.out").write_text(out_text(-1.0, self.seed_spin, ls=self.seed_ls,
                                                 total=self.seed_total))
        (sd / "rqz-frc-1.xyz").write_text(frc(0.0))
        return self.root

    def verdict(self):
        return q.reading(*q.load(self.write()))


class ReadingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Run(Path(self.tmp.name) / "run")

    def tearDown(self):
        self.tmp.cleanup()

    def test_yes_constant_offsets_cancel(self):
        self.r.delta["q1-c700"]["f05"] = 20.0          # one frame off by 20 meV
        v = self.r.verdict()
        self.assertEqual(v["verdict"], "yes")
        self.assertEqual(v["n_valid"], 12)
        # dE relative to the mean: 20 * (1 - 1/12) on f05
        self.assertAlmostEqual(v["D_meV"]["q1-c700_vs_q9-c2000"], 20.0 * 11 / 12, places=3)
        self.assertAlmostEqual(v["D_meV"]["q1-c2000_vs_q9-c2000"], 0.0, places=3)
        self.assertAlmostEqual(v["forces_meV_A"]["q1-c700_vs_q9-c2000"]["Fe"]["max"],
                               0.001 * q.nt.TO_MEV_A, places=6)
        self.assertTrue(v["checks"]["repro_ok"])

    def test_no_when_the_pseudopotential_moves_energies(self):
        for s in ("q1-c700", "q1-c2000"):
            self.r.delta[s]["f04"] = 80.0               # N3 frame: > 2 kT after centring
        v = self.r.verdict()
        self.assertEqual(v["verdict"], "no")
        self.assertGreater(v["D_meV"]["q1-c2000_vs_q9-c2000"], 2 * q.KT_MEV)
        self.assertGreater(v["strata"]["N3"]["q1-c2000_vs_q9-c2000"], 0.0)
        self.assertAlmostEqual(v["strata"]["EQ"]["q1-c2000_vs_q9-c2000"], 0.0, places=3)

    def test_inconclusive_when_only_the_grid_part_is_large(self):
        self.r.delta["q1-c700"]["f07"] = 40.0           # kT < 36.7 meV; control unchanged
        v = self.r.verdict()
        self.assertEqual(v["verdict"], "inconclusive")
        self.assertGreater(v["D_meV"]["q1-c700_vs_q9-c2000"], q.KT_MEV)
        self.assertGreater(v["D_meV"]["q1-c700_vs_q1-c2000"], q.KT_MEV)

    def test_threshold_edge(self):
        self.r.delta["q1-c700"]["f02"] = q.KT_MEV * 12 / 11 - 0.01   # D just below kT
        self.assertEqual(self.r.verdict()["verdict"], "yes")

    def test_invalid_frames_are_dropped_and_counted(self):
        self.r.spin[("q1-c700", "f03")] = LEGACY_SPIN + 0.02         # state changed
        self.r.unconv.add(("q9-c2000", "f08"))                       # SCF not converged
        self.r.delta["q1-c700"]["f03"] = 500.0                       # ignored: f03 invalid
        v = self.r.verdict()
        self.assertEqual(v["n_valid"], 10)
        self.assertNotIn("f03", v["valid"])
        self.assertEqual(v["verdict"], "yes")
        self.r.spin[("q1-c2000", "f11")] = LEGACY_SPIN - 0.011
        self.r.spin[("q9-c2000", "f12")] = LEGACY_SPIN + 0.05
        v = self.r.verdict()
        self.assertEqual((v["n_valid"], v["verdict"]), (8, "inconclusive"))

    def test_spin_tolerance_is_inclusive(self):
        self.r.spin[("q1-c700", "f03")] = LEGACY_SPIN + 0.0099
        self.assertEqual(self.r.verdict()["n_valid"], 12)

    def test_low_spin_fe_has_the_wider_tolerance(self):        # rule v2
        self.r.ls[("q1-c700", "f03")] = LEGACY_LS + 0.049             # valid
        self.r.ls[("q1-c2000", "f04")] = LEGACY_LS - 0.022            # valid (q1 seed value)
        self.r.ls[("q9-c2000", "f05")] = LEGACY_LS + 0.051            # invalid
        v = self.r.verdict()
        self.assertEqual(v["n_valid"], 11)
        self.assertNotIn("f05", v["valid"])
        self.assertAlmostEqual(v["max_dspin"]["q1-c700|f03"], 0.049, places=6)

    def test_total_spin_must_match_the_multiplicity(self):      # rule v2
        self.r.total[("q1-c700", "f06")] = 1.02
        v = self.r.verdict()
        self.assertEqual(v["n_valid"], 11)
        self.assertNotIn("f06", v["valid"])
        root = self.r.write()
        (root / "q9-c2000" / "f07" / "relabel.inp").write_text("&DFT\n&END DFT\n")  # no MULTIPLICITY
        v = q.reading(*q.load(root))
        self.assertNotIn("f07", v["valid"])

    def test_seed_state_test(self):                              # rule v2
        self.r.seed_ls = LEGACY_LS + 0.0223                           # q1 seed of 2026-11-27: passes
        v = self.r.verdict()
        self.assertTrue(v["checks"]["q1_seed"]["ok"])
        self.assertAlmostEqual(v["checks"]["q1_seed"]["dspin_ls"], 0.0223, places=6)
        self.assertEqual(v["checks"]["q1_seed"]["dspin_hs"], 0.0)
        self.assertEqual(v["verdict"], "yes")
        self.r.seed_total = 58.698103                                 # a collapse like job 4416
        v = self.r.verdict()
        self.assertFalse(v["checks"]["q1_seed"]["ok"])
        self.assertEqual(v["verdict"], "inconclusive")

    def test_failed_checks_make_it_inconclusive(self):
        self.r.seed_spin = LEGACY_SPIN + 0.1
        v = self.r.verdict()
        self.assertFalse(v["checks"]["q1_seed"]["ok"])
        self.assertEqual(v["verdict"], "inconclusive")
        self.r.seed_spin = LEGACY_SPIN
        self.r.repro_fx = 0.01 + 11.0 / q.nt.TO_MEV_A               # 11 meV/A off
        v = self.r.verdict()
        self.assertFalse(v["checks"]["repro_ok"])
        self.assertEqual(v["verdict"], "inconclusive")

    def test_missing_outputs(self):
        root = self.r.write()
        (root / "q1-c2000" / "f06" / "relabel.out").unlink()
        (root / "q9-c700" / "f10" / "relabel.out").unlink()
        v = q.reading(*q.load(root))
        self.assertNotIn("f06", v["valid"])
        self.assertIsNone(v["checks"]["repro_max_dF"]["f10"])
        self.assertEqual(v["verdict"], "inconclusive")

    def test_main_writes_tables(self):
        root = self.r.write()
        with redirect_stdout(io.StringIO()):
            q.main([str(root)])
        rows = (root / "analysis" / "frames.tsv").read_text().splitlines()
        self.assertEqual(len(rows), 1 + 2 + 3 * 12)
        f1 = [r.split("\t") for r in rows if r.startswith("f01\tEQ\t0\tt\tq1-c700")][0]
        self.assertEqual((f1[5], f1[6], f1[8], f1[12], f1[13]), ("True", "True", "True", "2", "364.3"))
        self.assertEqual((f1[14], f1[15], f1[16]), ("1.000", "0.0000", "0.0000"))
        v = json.loads((root / "analysis" / "verdict.json").read_text())
        self.assertEqual((v["reading"]["verdict"], v["reading"]["rule"]), ("yes", "v2"))
        self.assertIn("q1-c700_vs_q9-c2000\tNa\t", (root / "analysis" / "forces.tsv").read_text())


if __name__ == "__main__":
    unittest.main()
