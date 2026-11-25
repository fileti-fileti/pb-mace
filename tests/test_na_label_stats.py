"""Tests for src/na_label_stats.py (stdlib only)."""
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("na_label_stats", str(ROOT / "src" / "na_label_stats.py"))
ns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ns)

LAT = 'Lattice="10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0"'
PROPS = "Properties=species:S:1:pos:R:3:REF_forces:R:3"


def frame(ct, atoms):
    """atoms: [(el, fx, fy, fz)] -> one extxyz frame."""
    s = ["{}".format(len(atoms)),
         '{} {} REF_energy=-1.0 config_type={} grupo={}:0 pbc="T T T"'.format(LAT, PROPS, ct, ct)]
    for i, (el, fx, fy, fz) in enumerate(atoms):
        s.append("{} {:.3f} 0.0 0.0 {:.6f} {:.6f} {:.6f}".format(el, i * 1.0, fx, fy, fz))
    return "\n".join(s) + "\n"


def na_frame(ct, sum_x, n_na=4):
    """n_na Na + 1 Fe; the forces sum to (sum_x, 0, 0)."""
    atoms = [("Na", 0.5, 0.1, -0.2) for _ in range(n_na)]
    atoms.append(("Fe", sum_x - 0.5 * n_na, -0.1 * n_na, 0.2 * n_na))
    return frame(ct, atoms)


def fr(ct, x, n_na=4):
    return {"config_type": ct, "n_na": n_na, "sumF": x * n_na ** 0.5}


class ParseTest(unittest.TestCase):
    def test_read_frames(self):
        text = na_frame("interface_W4aTS", 2.0) + frame("vacancia_P1", [("Fe", 0.3, 0.0, 0.4)])
        f = ns.read_frames(text, "train")
        self.assertEqual([x["config_type"] for x in f], ["interface_W4aTS", "vacancia_P1"])
        self.assertEqual([x["n_na"] for x in f], [4, 0])
        self.assertAlmostEqual(f[0]["sumF"], 2.0, places=9)
        self.assertAlmostEqual(f[1]["sumF"], 0.5, places=9)

    def test_percentile(self):
        self.assertAlmostEqual(ns.percentile([4, 1, 3, 2], 50), 2.5)
        self.assertAlmostEqual(ns.percentile([1, 2, 3, 4], 90), 3.7)
        self.assertEqual(ns.percentile([7.0], 90), 7.0)


class ReadingTest(unittest.TestCase):
    def sample(self, ts_scale=1.0, ts_max=None):
        vals = [0.4, 0.5, 0.6, 0.7, 0.8]
        f = [fr(ct, v) for ct in ns.EQ for v in vals]
        f += [fr(ct, v * ts_scale) for ct in ns.TS for v in vals]
        f += [fr("interface_N3", v) for v in vals]
        if ts_max is not None:
            f.append(fr("interface_W4bTS", ts_max))
        return f

    def test_same(self):
        r = ns.reading(self.sample())
        self.assertEqual(r["verdict"], "same")
        self.assertAlmostEqual(r["r_p90"], 1.0)

    def test_ts_worse(self):
        self.assertEqual(ns.reading(self.sample(ts_scale=2.0))["verdict"], "TS worse")

    def test_inconclusive_when_only_the_max_moves(self):
        r = ns.reading(self.sample(ts_max=5.0))
        self.assertGreater(r["r_max"], 1.5)
        self.assertEqual(r["verdict"], "inconclusive")

    def test_n_na_normalisation(self):
        f = [fr(ct, 0.5, n_na=8) for ct in ns.EQ] + [fr(ct, 0.5, n_na=24) for ct in ns.TS]
        f += [fr("interface_N3", 0.5)]
        self.assertAlmostEqual(ns.reading(f)["r_p90"], 1.0)


class MainTest(unittest.TestCase):
    def test_end_to_end_and_test_split_never_opened(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "consolidado"
            d.mkdir()
            train = "".join(na_frame(ct, v) for ct in ns.EQ + ns.TS + ns.WINDOWS
                            for v in (1.0, 1.2, 1.4))
            train += frame("vacancia_P1", [("Fe", 0.1, 0.0, 0.0)])
            (d / "train.xyz").write_text(train)
            (d / "valid.xyz").write_text(na_frame("interface_longa", 1.1))
            (d / "test.xyz").write_text("not read")
            os.chmod(str(d / "test.xyz"), 0)
            sums = Path(tmp) / "consolidado.sha256"
            sums.write_text("".join("{}  consolidado/{}.xyz\n".format(
                ns.sha256(d / (s + ".xyz")), s) for s in ("train", "valid")))
            out = Path(tmp) / "out"
            with redirect_stdout(io.StringIO()):
                ns.main([str(d), "--sums", str(sums), "--out", str(out)])
            v = json.loads((out / "verdict.json").read_text())
            self.assertEqual(v["reading"]["verdict"], "same")
            self.assertEqual(v["reading"]["EQ"]["n"], 7)          # 6 train + 1 valid
            tsv = (out / "by_config_type.tsv").read_text()
            self.assertIn("vacancia_P1\t0\t|SF|\t1", tsv)
            self.assertEqual(len((out / "frames.tsv").read_text().splitlines()), 1 + 29)

    def test_checksum_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for s in ("train", "valid"):
                (d / (s + ".xyz")).write_text(na_frame("interface_aimd", 1.0))
            sums = d / "sums"
            sums.write_text("0" * 64 + "  consolidado/train.xyz\n")
            with self.assertRaises(ValueError):
                ns.main([str(d), "--sums", str(sums), "--out", str(d / "out")])


if __name__ == "__main__":
    unittest.main()
