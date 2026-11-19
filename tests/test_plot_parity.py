"""Tests for src/plot_parity.py. Need numpy and matplotlib: skipped under the stdlib-only
system python; run with mace_env: <env>/bin/python -m unittest tests.test_plot_parity"""
import importlib.util
import os
import sys
import tempfile
import unittest

try:
    import numpy as np
    import matplotlib  # noqa: F401
except ImportError:
    np = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "plot_parity.py")


def load():
    sys.path.insert(0, os.path.join(ROOT, "src"))
    spec = importlib.util.spec_from_file_location("plot_parity", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HDR = ('Lattice="10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0" '
       'Properties=species:S:1:pos:R:3:REF_forces:R:3{extra} REF_energy={e} '
       'config_type={ct}{pred} pbc="T T T"')


def write_pair(d, frames):
    """frames: (config_type, species, energy, pred energy, forces, pred forces)."""
    ref, ev = os.path.join(d, "ref.xyz"), os.path.join(d, "eval.xyz")
    with open(ref, "w") as r, open(ev, "w") as e:
        for k, (ct, sp, en, pe, f, pf) in enumerate(frames):
            r.write("{}\n{}\n".format(len(sp), HDR.format(extra="", e=en, ct=ct, pred="")))
            e.write("{}\n{}\n".format(len(sp), HDR.format(
                extra=":MACE_forces:R:3", e=en, ct=ct, pred=" MACE_energy={}".format(pe))))
            for i, s in enumerate(sp):
                pos = "{:.8f} 0.0 {:.8f}".format(i * 1.0, k * 0.1)
                fr = " ".join("{:.8f}".format(x) for x in f[i])
                fp = " ".join("{:.8f}".format(x) for x in pf[i])
                r.write("{} {} {}\n".format(s, pos, fr))
                e.write("{} {} {} {}\n".format(s, pos, fr, fp))
    return ev, ref


@unittest.skipIf(np is None, "numpy/matplotlib not available (run with mace_env)")
class TestPlotParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        z = [[0.0, 0.0, 0.0]] * 2
        self.frames = [
            ("a", ["O", "H"], -10.0, -9.998, [[1.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
             [[1.1, 0.0, 0.0], [0.0, 0.0, 0.0]]),
            ("a", ["O", "H"], -12.0, -12.002, z, z),
            ("b", ["Fe", "Fe", "C"], -30.0, -30.0, [[0.0] * 3] * 3,
             [[0.0, 0.0, -0.3], [0.0] * 3, [0.0] * 3]),
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_collect_and_centred_energies(self):
        d = self.m.collect(*write_pair(self.d, self.frames))
        self.assertEqual(list(d["n"]), [2, 2, 3])
        self.assertEqual(d["f_ref"].shape, (7, 3))
        er, ep = self.m.centred_energies(d)
        # composition O1H1: mean reference E/N = -5.5; Fe2C1 alone: -10
        np.testing.assert_allclose(er, [0.5, -0.5, 0.0])
        np.testing.assert_allclose(ep, [0.501, -0.501, 0.0])
        r, mae = self.m.rmse_mae(d["f_pred"] - d["f_ref"])
        self.assertAlmostEqual(r, np.sqrt((0.01 + 0.09) / 21))
        self.assertAlmostEqual(mae, 0.4 / 21)

    def test_mismatched_frames_refused(self):
        ev, ref = write_pair(self.d, self.frames)
        with open(ref) as fh:
            text = fh.read().replace("config_type=b", "config_type=c")
        with open(ref, "w") as fh:
            fh.write(text)
        self.assertEqual(self.m.main([ev, ref, os.path.join(self.d, "out")]), 1)
        self.assertFalse(os.path.exists(os.path.join(self.d, "out")))

    def test_main_writes_figures(self):
        ev, ref = write_pair(self.d, self.frames)
        out = os.path.join(self.d, "out")
        self.assertEqual(self.m.main([ev, ref, out, "--title", "t"]), 0)
        for f in ("parity.png", "forces_by_element.png"):
            self.assertTrue(os.path.getsize(os.path.join(out, f)) > 0)
        self.assertEqual(self.m.main([ev, ref, out]), 1)   # OUTDIR exists


if __name__ == "__main__":
    unittest.main()
