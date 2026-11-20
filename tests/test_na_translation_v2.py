"""Tests for the v2 (per_shift) reading of src/na_translation.py (stdlib only)."""
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import test_na_translation as t1   # synthetic CP2K output and the loaded module

nt, pt = t1.nt, t1.pt
LABEL = {"1": 0.3, "2": 4.5}       # legacy Fe spins, as run_info stores them
NSH = 8


def shift_forces(amp, k, host=0.0):
    """Na Fx = amp*sin(0.3 + 2*pi*k/NSH) (Ha/bohr); hosts get host*sin(...) on Fx."""
    w = math.sin(0.3 + 2 * math.pi * k / NSH)
    return [(el, (amp if el == "Na" else host) * w + 0.01, 0.02, -0.03) for el in t1.ELS]


def write_single(d, spins, energy, forces, grid, conv=True, ended=True):
    d.mkdir(parents=True)
    text = t1.out_text(grid, [spins], [energy], [conv])
    if not ended:
        text = text.replace("PROGRAM ENDED", "running")
    (d / "relabel.out").write_text(text)
    (d / "frc.xyz").write_text(pt.write_xyz([("i = 1", forces)]))


def make_run(base, name, frame, setting, amp, host=0.0, spins=None, seed="q9",
             seed_spins=None, grid=162, cell=10.17, skip=()):
    rd = base / name
    spins = spins or [[0.3, 4.5]] * NSH
    for k in range(NSH):
        if k in skip:
            continue
        write_single(rd / "shift_{}".format(k), spins[k], -1552.6 + 1e-5 * k,
                     shift_forces(amp, k, host), grid)
    if seed == "generate" and seed_spins is not None:
        write_single(rd / "seed_gen", seed_spins, -1552.6, shift_forces(amp, 0, host), grid)
    (rd / "ref_frc.xyz").write_text(pt.write_xyz([("label", shift_forces(amp, 0, host))]))
    h = cell / grid
    return name, {"frame": frame, "setting": setting, "forces_file": "frc.xyz", "cell_A": cell,
                  "shifts_A": [k * h / NSH for k in range(NSH)], "seed": seed,
                  "legacy_fe_spins": LABEL}


def run_all(runs, reading="v2"):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        info = {"commit": "abc", "layout": "per_shift", "reading": reading, "n_shifts": NSH,
                "runs": dict(runs(base))}
        (base / "run_info.json").write_text(json.dumps(info))
        with redirect_stdout(io.StringIO()):
            nt.main([str(base)])
        return json.loads((base / "analysis" / "verdict.json").read_text())


class V2Test(unittest.TestCase):
    def test_confirmed_fixed_and_q1(self):
        def runs(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02, host=0.0002)
            yield make_run(b, "cubo_puro-q9-c2400", "cubo_puro", "q9-c2400", amp=0.0001, grid=300)
            yield make_run(b, "cubo_puro-q1-c700", "cubo_puro", "q1-c700", amp=0.0001,
                           seed="generate", seed_spins=[0.8, 4.5],
                           spins=[[0.8, 4.5]] * NSH)          # q1 state: its own seed_gen
            yield make_run(b, "vacancia-q9-c700", "vacancia", "q9-c700", amp=0.0002, host=0.0002)
        v = run_all(runs)
        r = v["reading"]
        self.assertAlmostEqual(r["repro"], 0.0)
        self.assertEqual(r["diagnosis"], "confirmed")
        self.assertEqual(r["remedies"], {"cubo_puro-q1-c700": "fixed",
                                         "cubo_puro-q9-c2400": "fixed"})
        self.assertIn("Fe", r["q1_vs_q9_c2400"])
        self.assertAlmostEqual(r["q1_seed_gen_dspin_vs_label"], 0.5)
        self.assertEqual(v["rows"]["cubo_puro-q9-c700"]["valid"], [True] * NSH)
        self.assertEqual(v["rows"]["cubo_puro-q9-c2400"]["grid_n"], 300)

    def test_spin_tolerance_and_min_valid(self):
        def spins(n_off, k0_off=False):
            s = [[0.3, 4.5]] * NSH
            for k in range(NSH - n_off, NSH):
                s[k] = [0.3, 4.52]                            # 0.02 > 0.01: another state
            if k0_off:
                s[0] = [0.3, 4.52]
            return s
        def runs2(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02,
                           spins=spins(2))
        def runs3(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02,
                           spins=spins(3))
        def runs_k0(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02,
                           spins=spins(1, k0_off=True))
        self.assertEqual(run_all(runs2)["rows"]["cubo_puro-q9-c700"]["status"], "ok")
        v3 = run_all(runs3)
        self.assertEqual(v3["rows"]["cubo_puro-q9-c700"]["status"],
                         "inconclusive (5 valid shifts)")
        self.assertEqual(v3["reading"]["diagnosis"], "inconclusive")
        vk0 = run_all(runs_k0)["rows"]["cubo_puro-q9-c700"]    # shift 0 need not be valid
        self.assertEqual(vk0["status"], "ok")
        self.assertFalse(vk0["valid"][0])

    def test_reference_is_label_not_shift0(self):
        def runs(b):                                          # all shifts agree, label differs
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02,
                           spins=[[0.3, 4.6]] * NSH)
        v = run_all(runs)
        self.assertEqual(v["rows"]["cubo_puro-q9-c700"]["status"],
                         "inconclusive (0 valid shifts)")

    def test_unconverged_shift_not_valid(self):
        def runs(b):
            name, info = make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02)
            p = b / name / "shift_3" / "relabel.out"
            p.write_text(p.read_text().replace("outer SCF loop converged in   1 iterations",
                                               "outer SCF loop FAILED to converge"))
            yield name, info
        v = run_all(runs)
        self.assertFalse(v["rows"]["cubo_puro-q9-c700"]["valid"][3])

    def test_missing_shift_or_seed_gen(self):
        def runs(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02, skip=(5,))
            yield make_run(b, "cubo_puro-q1-c700", "cubo_puro", "q1-c700", amp=0.0001,
                           seed="generate", seed_spins=None)
        v = run_all(runs)
        self.assertEqual(v["rows"]["cubo_puro-q9-c700"]["status"], "not ended (7/8)")
        self.assertEqual(v["rows"]["cubo_puro-q1-c700"]["status"], "seed_gen not ended")
        self.assertEqual(v["reading"]["diagnosis"], "inconclusive")

    def test_layout_needs_v2_reading(self):
        def runs(b):
            yield make_run(b, "cubo_puro-q9-c700", "cubo_puro", "q9-c700", amp=0.02)
        with self.assertRaises(ValueError):
            run_all(runs, reading="v1")


if __name__ == "__main__":
    unittest.main()
