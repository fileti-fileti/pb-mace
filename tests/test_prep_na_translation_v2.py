"""Tests for scripts/prep_na_translation_v2.py (stdlib only)."""
import json
import os
import unittest
from pathlib import Path

from helpers import TempRepo, run  # noqa: F401  (helpers puts scripts/ on sys.path)

import prep_na_translation as pt
import prep_na_translation_v2 as p2
import test_prep_na_translation as v1

BASE = v1.BASE_INP.replace(
    "      EXTRAPOLATION USE_GUESS\n",
    "      EXTRAPOLATION USE_GUESS\n    &END QS\n    &SCF\n      SCF_GUESS ATOMIC\n"
    "    &END SCF\n    &QS\n").replace(
    "      POTENTIAL GTH-PBE-q16\n",
    "      POTENTIAL GTH-PBE-q16\n      &DFT_PLUS_U on\n        INIT_U_RAMPING_EACH_SCF T\n"
    "        L 2\n        U_MINUS_J [eV] 6.0\n        U_RAMPING [eV] 0.5\n      &END DFT_PLUS_U\n")
LEGACY_OUT = """                     Mulliken Population Analysis

 #  Atom  Element  Kind  Atomic population (alpha,beta) Net charge  Spin moment
      1     Fe       1         9.9     5.4     0.6     4.536083
      2     Na       2         4.5     4.5     1.0     0.000000
 # Total charge and spin      1.0   1.0    0.0   1.0
  outer SCF loop converged in   2 iterations
 ENERGY| Total FORCE_EVAL ( QS ) energy [a.u.]:            -1552.610466241634640
                     Mulliken Population Analysis

 #  Atom  Element  Kind  Atomic population (alpha,beta) Net charge  Spin moment
      1     Fe       1         9.9     5.4     0.6     4.500000
      2     Na       2         4.5     4.5     1.0     0.000000
 # Total charge and spin      1.0   1.0    0.0   1.0
  outer SCF loop converged in   2 iterations
 ENERGY| Total FORCE_EVAL ( QS ) energy [a.u.]:            -1552.6
"""


class InputTest(unittest.TestCase):
    def test_seeded_and_gen_inputs(self):
        text, gen = p2.build_inputs(BASE, {"cutoff": 1600, "rel_cutoff": 70})
        for t in (text, gen):
            self.assertEqual(pt.kw_values(t, "CUTOFF"), ["1600"])
            self.assertEqual(pt.kw_values(t, "PRINT_LEVEL"), ["MEDIUM"])
            self.assertEqual(pt.kw_values(t, "LAST_SNAPSHOT"), ["1"])
            self.assertEqual(pt.kw_values(t, "STEPS"), ["1"])
            self.assertEqual(pt.kw_values(t, "EXTRAPOLATION"), ["USE_GUESS"])
        self.assertEqual(pt.kw_values(text, "SCF_GUESS"), ["RESTART"])
        self.assertEqual(pt.kw_values(text, "WFN_RESTART_FILE_NAME"), ["seed.wfn"])
        self.assertEqual(pt.kw_values(text, "U_RAMPING"), ["[eV] 0.0"])
        self.assertEqual(pt.kw_values(text, "INIT_U_RAMPING_EACH_SCF"), [])
        self.assertEqual(pt.kw_values(gen, "SCF_GUESS"), ["ATOMIC"])       # label protocol
        self.assertEqual(pt.kw_values(gen, "U_RAMPING"), ["[eV] 0.5"])
        self.assertEqual(pt.kw_values(gen, "INIT_U_RAMPING_EACH_SCF"), ["T"])
        self.assertEqual(pt.kw_values(gen, "WFN_RESTART_FILE_NAME"), [])
        self.assertEqual(pt.kw_values(text, "U_MINUS_J"), ["[eV] 6.0"])    # physics untouched

    def test_wfn_line_goes_into_dft_with_na_swap(self):
        text, _ = p2.build_inputs(BASE, {"cutoff": 700, "rel_cutoff": 70, "na": v1.NA_Q1})
        dft = text[text.index("&DFT"):text.index("&MGRID")]
        self.assertIn("WFN_RESTART_FILE_NAME seed.wfn", dft)
        self.assertEqual(pt.kinds(text)["Na"]["potential_file"], "POTENTIAL_UZH")

    def test_refuses_non_label_protocol(self):
        with self.assertRaises(pt.PrepError):
            p2.build_inputs(BASE.replace("SCF_GUESS ATOMIC", "SCF_GUESS RESTART"),
                            {"cutoff": 700, "rel_cutoff": 70})
        with self.assertRaises(pt.PrepError):
            p2.build_inputs(BASE.replace("U_RAMPING [eV] 0.5", "U_RAMPING [eV] 0.0"),
                            {"cutoff": 700, "rel_cutoff": 70})
        with self.assertRaises(pt.PrepError):
            p2.build_inputs(BASE.replace("        INIT_U_RAMPING_EACH_SCF T\n", ""),
                            {"cutoff": 700, "rel_cutoff": 70})

    def test_legacy_spins(self):
        self.assertEqual(p2.legacy_fe_spins(LEGACY_OUT, 1), {"1": 4.536083})
        self.assertEqual(p2.legacy_fe_spins(LEGACY_OUT, 2), {"1": 4.5})
        with self.assertRaises(pt.PrepError):
            p2.legacy_fe_spins(LEGACY_OUT, 3)


class PrepareTest(v1.PrepareTest):
    """Same fake legacy tree as v1, with a label-protocol input, a legacy output and seeds."""

    def setUp(self):
        super().setUp()
        d = self.legacy / "sysA" / "b01"
        (d / "relabel.inp").write_text(BASE)
        (d / "relabel.out").write_text(LEGACY_OUT)
        seeds = self.t.repo / "runs" / "v1" / "c"
        seeds.mkdir(parents=True)
        (seeds / "rqz-RESTART.wfn").write_bytes(b"wfn-bytes")
        self.cfg["n_shifts"] = 8
        self.cfg["frames"]["a"]["grid_n"] = {"700": 160}
        self.cfg["frames"]["a"]["seeds"] = {"q9": "runs/v1/c/rqz-RESTART.wfn"}
        self.cfg["settings"]["c700"]["seed"] = "q9"
        self.cfg["settings"]["q1"]["seed"] = "generate"

    def prep(self, name="T"):
        return p2.prepare(self.t.repo, "configs/t.json", name, machine="neumann", mcfg=self.mcfg)

    def test_run_dirs(self):
        self.commit_cfg()
        out, cmds = self.prep()
        self.assertEqual(len(cmds), 2)
        rd = out / "a-c700"
        self.assertEqual((rd / "seed.wfn").read_bytes(), b"wfn-bytes")
        h = 10.170 / 160                                   # grid_n from the config, not the rule
        for k in range(8):
            sd = rd / "shift_{}".format(k)
            a = pt.read_xyz_frame((sd / "pool.xyz").read_text(), 1, "pool")[2]
            self.assertAlmostEqual(a[1][1], 2.6 + k * h / 8, places=9)
            self.assertEqual((sd / "relabel.inp").read_text(), (rd / "relabel.inp").read_text())
            self.assertEqual(os.readlink(str(sd / "seed.wfn")), os.path.join("..", "seed.wfn"))
            self.assertTrue((sd / "BASIS_MOLOPT").is_file())
        self.assertFalse((rd / "seed_gen").exists())
        job = (rd / "job.sh").read_text()
        self.assertIn("for k in $(seq 0 7)", job)
        self.assertNotIn("seed_gen", job)
        q1 = out / "a-q1"
        self.assertFalse((q1 / "seed.wfn").exists())     # written by the job
        self.assertEqual(pt.kw_values((q1 / "seed_gen" / "relabel.inp").read_text(), "SCF_GUESS"),
                         ["ATOMIC"])
        self.assertIn("cp seed_gen/rqz-RESTART.wfn seed.wfn", (q1 / "job.sh").read_text())
        info = json.loads((out / "run_info.json").read_text())
        r = info["runs"]["a-c700"]
        self.assertEqual(r["legacy_fe_spins"], {"1": 4.5})   # snapshot 2 of the legacy output
        self.assertEqual(r["grid_n_used"], 160)
        self.assertEqual(r["files"]["seed.wfn"]["source"],
                         str((self.t.repo / "runs/v1/c/rqz-RESTART.wfn").resolve()))
        self.assertEqual(info["reading"], "v2")

    def test_missing_seed_refused(self):
        self.cfg["frames"]["a"]["seeds"] = {"q9": "runs/v1/c/nope.wfn"}
        self.commit_cfg()
        with self.assertRaises(pt.PrepError):
            self.prep()

    def test_config_checks(self):
        super().test_config_checks()
        cfg = json.loads(json.dumps(self.cfg))
        cfg["settings"]["c700"]["seed"] = "q7"
        self.commit_cfg(cfg)
        with self.assertRaises(pt.PrepError):
            self.prep()


del v1.PrepareTest   # keep unittest from collecting the v1 class twice

if __name__ == "__main__":
    unittest.main()
