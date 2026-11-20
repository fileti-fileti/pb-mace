"""Tests for src/na_translation.py (stdlib only)."""
import importlib.util
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("na_translation", str(ROOT / "src" / "na_translation.py"))
nt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nt)
pt = nt.pt

ELS = ["Fe", "Fe", "C", "N", "Na"]


def out_text(n_grid, spins, energies, conv=None):
    """Synthetic CP2K output: grid block, then per step Mulliken + SCF status + ENERGY."""
    conv = conv or [True] * len(spins)
    s = [" PW_GRID| Information for grid number                                          1",
         " PW_GRID|   Bounds   1            -81      80                Points:         {}".format(n_grid),
         " PW_GRID| Information for grid number                                          2",
         " PW_GRID|   Bounds   1            -48      47                Points:          96"]
    for sp, e, c in zip(spins, energies, conv):
        s.append("  *** SCF run converged in    10 steps ***")
        s.append("  outer SCF loop converged in   1 iterations" if c
                 else "  outer SCF loop FAILED to converge after   10 iterations")
        s += ["                     Mulliken Population Analysis", "",
              " #  Atom  Element  Kind  Atomic population (alpha,beta) Net charge  Spin moment"]
        for i, el in enumerate(ELS, 1):
            spin = sp[i - 1] if el == "Fe" else 0.0
            s.append("      {}     {}       1    8.0  7.0  0.1  {:.6f}".format(i, el, spin))
        s.append(" # Total charge and spin      1.0   1.0    0.0   1.0")
        s.append(" ENERGY| Total FORCE_EVAL ( QS ) energy [a.u.]:            {:.12f}".format(e))
    s.append("  **** **** ******  **  PROGRAM ENDED AT  ****")
    return "\n".join(s) + "\n"


def forces_for(amp, phase0, nsh=4, host=0.0):
    """Na Fx = amp*sin(phase0 + k*pi/2) (Ha/bohr); hosts get host*sin(...) on Fx."""
    frames = []
    for k in range(nsh):
        w = math.sin(phase0 + k * math.pi / 2)
        atoms = []
        for el in ELS:
            fx = amp * w if el == "Na" else host * w
            atoms.append((el, fx + 0.01, 0.02, -0.03))
        frames.append(("i = {}".format(k + 1), atoms))
    return frames


def make_run(base, name, frame, setting, amp, host=0.0, spins=None, conv=None, grid=162,
             cell=10.17):
    rd = base / name
    rd.mkdir()
    spins = spins or [[0.3, 4.5]] * 4
    (rd / "relabel.out").write_text(out_text(grid, spins, [-1552.6, -1552.6001, -1552.6, -1552.5999],
                                             conv))
    fr = forces_for(amp, 0.3, host=host)
    (rd / "frc.xyz").write_text(pt.write_xyz(fr))
    (rd / "ref_frc.xyz").write_text(pt.write_xyz([fr[0]]))
    h = cell / grid
    return name, {"frame": frame, "setting": setting, "forces_file": "frc.xyz", "cell_A": cell,
                  "shifts_A": [k * h / 4 for k in range(4)]}


class ParseTest(unittest.TestCase):
    def test_parse_out(self):
        p = nt.parse_out(out_text(162, [[0.3, 4.5], [0.31, 4.4]], [-1.0, -1.5], [True, False]))
        self.assertTrue(p["ended"])
        self.assertEqual(p["grid_n"], 162)                    # grid 1, not grid 2
        self.assertEqual(len(p["steps"]), 2)
        self.assertEqual(p["steps"][0]["fe_spins"], {1: 0.3, 2: 4.5})
        self.assertEqual([s["converged"] for s in p["steps"]], [True, False])


class StatsTest(unittest.TestCase):
    def test_sinusoid_spread(self):
        a = 0.01   # Ha/bohr
        f = [atoms for _, atoms in forces_for(a, 0.7)]
        s, sumf = nt.spread_stats(f, [True] * 4)
        # population std of a*sin over 4 quarter phases = a/sqrt(2); only x varies -> /sqrt(3)
        self.assertAlmostEqual(s["Na"], a / math.sqrt(6) * nt.TO_MEV_A, places=6)
        self.assertAlmostEqual(s["Fe"], 0.0, places=9)
        self.assertEqual(len(sumf), 4)

    def test_invalid_shift_dropped(self):
        f = [atoms for _, atoms in forces_for(0.01, 0.0)]
        s3, _ = nt.spread_stats(f, [True, True, True, False])
        s4, _ = nt.spread_stats(f, [True] * 4)
        self.assertNotAlmostEqual(s3["Na"], s4["Na"])


class ReadingTest(unittest.TestCase):
    def run_all(self, runs):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            info = {"commit": "abc", "runs": dict(runs(base))}
            (base / "run_info.json").write_text(json.dumps(info))
            with redirect_stdout(io.StringIO()):
                nt.main([str(base)])
            v = json.loads((base / "analysis" / "verdict.json").read_text())
            self.assertTrue((base / "analysis" / "summary.tsv").is_file())
            return v

    def test_confirmed_and_fixed(self):
        def runs(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02, host=0.0002)
            yield make_run(b, "cubo_puro-q9-c1600", "cubo_puro", "q9-c1600", amp=0.0001, grid=256)
            yield make_run(b, "vacancia-q9-c700", "vacancia", "q9-c700", amp=0.0002, host=0.0002)
        v = self.run_all(runs)["reading"]
        self.assertAlmostEqual(v["repro"], 0.0)
        self.assertEqual(v["diagnosis"], "confirmed")
        self.assertEqual(v["remedies"], {"cubo_puro-q9-c1600": "fixed"})

    def test_refuted_and_not_fixed(self):
        def runs(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.0005, host=0.0004)
            yield make_run(b, "cubo_puro-q9-c400", "cubo_puro", "q9-c400", amp=0.05)
            yield make_run(b, "vacancia-q9-c700", "vacancia", "q9-c700", amp=0.0, host=0.0001)
        v = self.run_all(runs)["reading"]
        self.assertEqual(v["diagnosis"], "refuted")
        self.assertEqual(v["remedies"], {"cubo_puro-q9-c400": "not fixed"})

    def test_spin_state_change_makes_run_inconclusive(self):
        bad = [[0.3, 4.5], [0.3, 3.0], [0.3, 3.0], [0.3, 4.5]]   # 2 shifts change state
        def runs(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02, spins=bad)
        v = self.run_all(runs)
        self.assertEqual(v["rows"]["cubo_puro-q9-c700"]["status"], "inconclusive (2 valid shifts)")
        self.assertEqual(v["reading"]["diagnosis"], "inconclusive")

    def test_unfinished_run(self):
        def runs(b):
            name, info = make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02)
            p = b / name / "relabel.out"
            p.write_text(p.read_text().replace("PROGRAM ENDED", "running"))
            yield name, info
        v = self.run_all(runs)
        self.assertEqual(v["rows"]["cubo_puro-q9-c700"]["status"], "not ended")


if __name__ == "__main__":
    unittest.main()
