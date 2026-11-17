"""Tests for src/rdf.py. Need numpy: skipped under the stdlib-only system python;
run with the analysis env: <env>/bin/python -m unittest tests.test_rdf"""
import importlib.util
import os
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "rdf.py")


def load_rdf():
    spec = importlib.util.spec_from_file_location("rdf", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipIf(np is None, "numpy not available (run with the analysis env)")
class TestRdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rdf = load_rdf()

    def test_ideal_gas_same_species(self):
        L = 10.0
        frames = np.random.RandomState(1).uniform(0, L, size=(200, 300, 3))
        idx = np.arange(300)
        edges = self.rdf.bin_edges([L, L, L], 0.1)
        r, g, err, n, _, _ = self.rdf.partial_rdf(frames, idx, idx, [L, L, L], edges, 5)
        self.assertAlmostEqual(edges[-1], 5.0)
        self.assertLess(abs(g[r > 1.0].mean() - 1.0), 0.02)

    def test_ideal_gas_two_species(self):
        L = 8.0
        frames = np.random.RandomState(2).uniform(0, L, size=(200, 200, 3))
        edges = self.rdf.bin_edges([L, L, L], 0.1)
        r, g, err, n, _, _ = self.rdf.partial_rdf(
            frames, np.arange(100), np.arange(100, 200), [L, L, L], edges, 5)
        self.assertLess(abs(g[r > 1.0].mean() - 1.0), 0.02)
        self.assertAlmostEqual(n[-1], 100 * 4 / 3 * np.pi * edges[-1] ** 3 / L ** 3, delta=1.0)

    def test_simple_cubic_shells(self):
        a, m = 1.0, 4
        grid = np.array([[i, j, k] for i in range(m) for j in range(m) for k in range(m)], float)
        frames = (a * grid)[None, :, :]
        idx = np.arange(len(grid))
        edges = self.rdf.bin_edges([m * a] * 3, 0.05)
        r, g, err, n, _, _ = self.rdf.partial_rdf(frames, idx, idx, [m * a] * 3, edges, 2)
        upper = edges[1:]
        self.assertTrue(np.all(n[(upper > 1.01) & (upper < 1.40)] == 6))
        self.assertTrue(np.all(n[(upper > 1.42) & (upper < 1.70)] == 18))

    def test_stitch_last_branch_wins(self):
        def frame(step, x):
            return "1\n i = {}, time = {}.000, E = -1.0\n H {} 0.0 0.0\n".format(step, step, x)
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = os.path.join(d, "a.xyz"), os.path.join(d, "b.xyz")
            with open(p1, "w") as f:
                f.write("".join(frame(s, 1.0) for s in (0, 10, 20, 30)))
            with open(p2, "w") as f:
                f.write("".join(frame(s, 2.0) for s in (20, 30, 40)))
            steps, times, sym, frames = self.rdf.stitch([p1, p2])
        self.assertEqual(steps.tolist(), [0, 10, 20, 30, 40])
        self.assertEqual(frames[:, 0, 0].tolist(), [1.0, 1.0, 2.0, 2.0, 2.0])
        self.assertEqual(sym, ["H"])

    def test_kinds_and_elements(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "COORD.inc")
            with open(p, "w") as f:
                f.write("&COORD\n  Fe2 0 0 0\n  Fe3_up 1 0 0\n  Na 0 1 0\n&END COORD\n")
            kinds = self.rdf.read_kinds(p)
        self.assertEqual(kinds, ["Fe2", "Fe3_up", "Na"])
        self.assertEqual([self.rdf.element(k) for k in kinds], ["Fe", "Fe", "Na"])


if __name__ == "__main__":
    unittest.main()
