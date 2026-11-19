"""Tests for src/rdf_compare.py (the RDF reading rule). Need numpy: skipped under the
stdlib-only system python; run with mace_env: <env>/bin/python -m unittest tests.test_rdf_compare"""
import importlib.util
import os
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DR = 0.02
R = DR * (np.arange(250) + 0.5) if np is not None else None


def load():
    spec = importlib.util.spec_from_file_location("rdf_compare",
                                                  os.path.join(ROOT, "src", "rdf_compare.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def curve(r0=2.0, h=5.0, w=0.08):
    """Contact peak at r0, minimum near r0 + 0.6, second shell at r0 + 1.4 (g -> ~1)."""
    g = h * np.exp(-0.5 * ((R - r0) / w) ** 2) + 1.2 * np.exp(-0.5 * ((R - r0 - 1.4) / 0.3) ** 2)
    g[R < r0 - 0.5] = 0.0
    n = np.cumsum(g * 4 * np.pi * R ** 2 * DR) * 0.05     # density 0.05 / A^3
    return g, n


def write_dat(path, g, n, gerr=None):
    gerr = np.zeros_like(g) if gerr is None else gerr
    np.savetxt(path, np.column_stack([R, g, gerr, n]), fmt="%.8f",
               header="test\nr_A g g_err n_within_r_upper")


def write_blocks(path, gs, ns):
    np.savetxt(path, np.column_stack([R] + list(gs) + list(ns)), fmt="%.8f", header="test")


@unittest.skipIf(np is None, "numpy not available (run with mace_env)")
class TestRdfCompare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.aimd = os.path.join(self.tmp.name, "aimd")
        self.mlmd = os.path.join(self.tmp.name, "mlmd")
        os.mkdir(self.aimd)
        os.mkdir(self.mlmd)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, system, pair, aimd_r0, mlmd_r0s, blocks=None):
        """AIMD curve at aimd_r0 (g_err 0.1); one replica per mlmd_r0; optional replica blocks
        (peak positions of each replica's blocks)."""
        g, n = curve(aimd_r0)
        write_dat(os.path.join(self.aimd, "rdf_{}_{}.dat".format(system, pair)), g, n,
                  np.full_like(g, 0.1))
        for k, r0 in enumerate(mlmd_r0s, 1):
            gm, nm = curve(r0)
            p = os.path.join(self.mlmd, "rdf_{}_r{}_{}.dat".format(system, k, pair))
            write_dat(p, gm, nm)
            if blocks is not None:
                bl = [curve(b) for b in blocks]
                write_blocks(p[:-4] + "_blocks.dat", [b[0] for b in bl], [b[1] for b in bl])

    def test_window_and_quantities(self):
        g, n = curve(2.013)
        imax, jmin = self.m.first_peak_window(g)
        self.assertAlmostEqual(R[imax], 2.01, delta=0.03)
        self.assertTrue(2.3 < R[jmin] < 3.0)
        q = self.m.peak_quantities(R, g, n, jmin)
        self.assertAlmostEqual(q["r1"], 2.013, delta=0.002)       # parabola refines the bin
        self.assertAlmostEqual(q["n1"], n[jmin])
        self.assertAlmostEqual(q["g1"], g[np.argmax(g[:jmin + 1])])

    def test_no_minimum_and_no_maximum(self):
        g = np.where(R > 1.0, 1.0 - np.exp(-(R - 1.0)), 0.0)      # rises to the end
        self.assertEqual(self.m.first_peak_window(g), (None, None))
        g2, _ = curve()
        g2[R > 2.0] = 5.0 * np.exp(-(R[R > 2.0] - 2.0))            # peak, then decays to r_max
        imax, jmin = self.m.first_peak_window(g2)
        self.assertIsNotNone(imax)
        self.assertIsNone(jmin)

    def test_verdict_rule(self):
        v = self.m.verdict
        self.assertEqual(v(0.01, 0.01, 0.05), "yes")         # 0.03 <= 0.05
        self.assertEqual(v(0.10, 0.01, 0.05), "no")          # 0.08 > 0.05
        self.assertEqual(v(0.01, 0.03, 0.05), "inconclusive")
        self.assertEqual(self.m.combine(["yes", "inconclusive"]), "inconclusive")
        self.assertEqual(self.m.combine(["yes", "no"]), "no")
        self.assertEqual(self.m.combine(["NA"]), "NA")

    def test_run_yes_no_inconclusive(self):
        self.make("s", "Fe2-C", 2.0, [2.000, 2.001, 1.999, 2.000, 2.000])     # framework: yes
        self.make("s", "O-O", 2.0, [2.20, 2.201, 2.199, 2.20, 2.20])          # water: r1 off
        self.make("s", "Na-N", 2.0, [1.90, 2.10, 1.95, 2.05, 2.00])           # Na: spread
        comp, ver = self.m.run(self.aimd, self.mlmd, 5, [])
        got = {(s, g): v for s, g, v, _, _ in ver}
        self.assertEqual(got[("s", "framework")], "yes")
        self.assertEqual(got[("s", "water")], "no")
        self.assertEqual(got[("s", "Na")], "inconclusive")
        g1 = [row for row in comp if row[1] == "Fe2-C" and row[4] == "g1"][0]
        self.assertEqual(g1[12], "descriptive")
        self.assertAlmostEqual(g1[6], 0.1)                     # AIMD g_err at the g1 bin
        self.assertIsNone(g1[13])                              # no replica blocks written

    def test_sigma_from_replica_spread(self):
        r0s = [1.98, 2.02, 1.99, 2.01, 2.00]
        self.make("s", "C-N", 2.0, r0s, blocks=[1.99, 2.01, 2.00, 2.00, 2.00])
        rows, rc = self.m.compare_pair(
            os.path.join(self.aimd, "rdf_s_C-N.dat"),
            [os.path.join(self.mlmd, "rdf_s_r{}_C-N.dat".format(k)) for k in range(1, 6)])
        r1 = [r for r in rows if r[0] == "r1"][0]
        self.assertIsNone(r1[2])                               # no AIMD error in the rule
        self.assertAlmostEqual(r1[4], float(np.std(r0s, ddof=1)), delta=0.001)
        self.assertAlmostEqual(r1[5], r1[4] * np.sqrt(1.2))    # sigma = s sqrt(1 + 1/5)
        self.assertGreater(r1[9], 0.0)                         # replica 5-block error reported
        self.assertTrue(2.3 < rc < 3.0)

    def test_unstable_replica_makes_system_no(self):
        self.make("s", "Fe2-C", 2.0, [2.0, 2.0, 2.0, 2.0, 2.0])
        os.remove(os.path.join(self.mlmd, "rdf_s_r5_Fe2-C.dat"))
        comp, ver = self.m.run(self.aimd, self.mlmd, 5, ["s_r5"])
        self.assertEqual(ver[0][2], "no")
        self.assertEqual(ver[0][4], "s_r5")
        with self.assertRaises(ValueError):
            self.m.run(self.aimd, self.mlmd, 5, [])            # r5 missing and not unstable

    def test_pair_outside_groups_refused(self):
        self.make("s", "Fe2-N", 2.0, [2.0] * 5)
        with self.assertRaises(ValueError):
            self.m.run(self.aimd, self.mlmd, 5, [])


if __name__ == "__main__":
    unittest.main()
