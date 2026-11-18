"""Tests for src/mace_errors.py: extxyz parsing, frame matching, errors by hand, refusals."""
import importlib.util
import os
import tempfile
import unittest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "src", "mace_errors.py")
spec = importlib.util.spec_from_file_location("mace_errors", SRC)
me = importlib.util.module_from_spec(spec)
spec.loader.exec_module(me)

LAT = 'Lattice="10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0"'
REF = (
    "2\n{} Properties=species:S:1:pos:R:3:REF_forces:R:3 REF_energy=-10.0 config_type=w "
    'grupo=w:1 pbc="T T T"\n'
    "O 0.00000000 0.00000000 0.00000000 0.00000000 0.00000000 0.00000000\n"
    "H 0.95000000 0.00000000 0.00000000 0.00000000 0.00000000 0.00000000\n"
    "1\n{} Properties=species:S:1:pos:R:3:REF_forces:R:3 REF_energy=-5.0 config_type=x "
    'pbc="T T T"\n'
    "O 1.00000000 1.00000000 1.00000000 1.00000000 1.00000000 1.00000000\n").format(LAT, LAT)
EVAL = (
    "2\n{} Properties=species:S:1:pos:R:3:REF_forces:R:3:MACE_forces:R:3 REF_energy=-10.0 "
    'MACE_energy=-9.998 config_type=w grupo=w:1 pbc="T T T"\n'
    "O 0.00000000 0.00000000 0.00000000 0 0 0 0.00300000 0.00000000 0.00000000\n"
    "H 0.95000000 0.00000000 0.00000000 0 0 0 0.00000000 -0.00400000 0.00000000\n"
    "1\n{} Properties=species:S:1:pos:R:3:REF_forces:R:3:MACE_forces:R:3 REF_energy=-5.0 "
    'MACE_energy=-5.003 config_type=x pbc="T T T"\n'
    "O 1.00000000 1.00000000 1.00000000 1 1 1 1.00000000 1.00000000 1.00600000\n\n"
).format(LAT, LAT)

# By hand (meV): dE/N = +1 (w), -3 (x); force components w: 3,0,0,0,-4,0; x: 0,0,6.
EXPECTED = {
    ("all", "all"): ["2", "3", "2.236", "2.000", "2.603", "1.444"],
    ("config_type", "w"): ["1", "2", "1.000", "1.000", "2.041", "1.167"],
    ("config_type", "x"): ["1", "1", "3.000", "3.000", "3.464", "2.000"],
    ("element", "H"): ["1", "1", "NA", "NA", "2.309", "1.333"],
    ("element", "O"): ["2", "2", "NA", "NA", "2.739", "1.500"],
}


class MaceErrorsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        p = os.path.join(self.d, name)
        with open(p, "w") as f:
            f.write(text)
        return p

    def run_main(self, eval_text=EVAL, ref_text=REF, out="out"):
        out = os.path.join(self.d, out)
        rc = me.main([self.write("eval.xyz", eval_text), self.write("ref.xyz", ref_text), out])
        return rc, out

    def read_tsv(self, path):
        with open(path) as f:
            return [line.rstrip("\n").split("\t") for line in f]

    def test_parse_comment(self):
        info = me.parse_comment('{} a=1 b="x y" c=T:2'.format(LAT))
        self.assertEqual(info["Lattice"], "10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0")
        self.assertEqual((info["a"], info["b"], info["c"]), ("1", "x y", "T:2"))

    def test_errors_by_hand(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 0)
        rows = self.read_tsv(os.path.join(out, "errors.tsv"))
        self.assertEqual(tuple(rows[0]), me.COLUMNS)
        got = {(r[0], r[1]): r[2:] for r in rows[1:]}
        self.assertEqual(got, EXPECTED)
        frames = self.read_tsv(os.path.join(out, "frame_errors.tsv"))
        self.assertEqual(frames[1], ["0", "w", "2", "1.000", "2.041"])
        self.assertEqual(frames[2], ["1", "x", "1", "-3.000", "3.464"])

    def refused(self, eval_text=EVAL, ref_text=REF):
        rc, out = self.run_main(eval_text, ref_text, out="refused")
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(out))

    def test_refusals(self):
        one_frame = REF.split("1\n" + LAT)[0]
        self.refused(ref_text=one_frame)                                   # frame count
        self.refused(ref_text=REF.replace("\nH ", "\nN "))                 # species
        self.refused(ref_text=REF.replace("H 0.95", "H 0.96"))             # positions
        self.refused(ref_text=REF.replace("config_type=x", "config_type=y"))
        self.refused(eval_text=EVAL.replace("MACE_energy=-5.003 ", ""))    # no prediction
        self.refused(eval_text=EVAL.replace("MACE_forces", "OTHER_forces"))
        self.refused(eval_text=EVAL.replace(" 1.00600000\n", "\n"))        # short line
        self.refused(eval_text=EVAL.rstrip("\n").rsplit("\n", 1)[0] + "\n")  # truncated

    def test_existing_outdir_refused(self):
        os.makedirs(os.path.join(self.d, "out"))
        rc, _ = self.run_main()
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
