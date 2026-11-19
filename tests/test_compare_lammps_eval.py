"""compare_lammps_eval.py: energy and force agreement, benchmark rate, mismatches."""
import importlib.util
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "compare_lammps_eval", os.path.join(ROOT, "src", "compare_lammps_eval.py"))
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

LOG = ("LAMMPS (10 Sep 2025)\nrun 0\nPerformance: 0.000 ns/day, 0.000 hours/ns, 0.000 timesteps/s\n"
       "PE_START -100.0000000000\nrun 200\n"
       "Performance: 1.234 ns/day, 19.4 hours/ns, 14.282 timesteps/s, 99.0% CPU use\n")
FORCES = [(0.1, -0.2, 0.3), (-0.1, 0.2, -0.3)]


def dump(forces, ids=(2, 1), elements=("O", "H")):
    rows = sorted(zip(ids, elements, forces), reverse=True)
    out = ["ITEM: TIMESTEP", "0", "ITEM: NUMBER OF ATOMS", str(len(rows)),
           "ITEM: BOX BOUNDS pp pp pp", "0 10", "0 10", "0 10", "ITEM: ATOMS id element fx fy fz"]
    out += ["{} {} {:.10f} {:.10f} {:.10f}".format(i, e, *f) for i, e, f in rows]
    return "\n".join(out) + "\n"


def eval_xyz(energy, forces, species=("H", "O")):
    out = ["2", 'Lattice="10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0" '
           'Properties=species:S:1:pos:R:3:MACE_forces:R:3 MACE_energy={} pbc="T T T"'.format(energy)]
    out += ["{} {:.1f} 0.0 0.0 {:.10f} {:.10f} {:.10f}".format(s, k, *f)
            for k, (s, f) in enumerate(zip(species, forces))]
    return "\n".join(out) + "\n"


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = os.path.join(self.tmp.name, "box")
        os.mkdir(self.d)
        self.write(LOG, dump([FORCES[1], FORCES[0]]), eval_xyz(-100.0000005, FORCES))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, log, dmp, ev):
        for name, text in (("log.lammps", log), ("forces.dump", dmp), ("eval.xyz", ev)):
            with open(os.path.join(self.d, name), "w") as f:
                f.write(text)

    def test_pass(self):
        # dump ids 2,1 hold (O, f1), (H, f0): sorted by id -> H f0, O f1, as eval.xyz
        row = cl.compare(self.d)
        self.assertEqual(row[0], "box")
        self.assertEqual(row[1], "2")
        self.assertEqual(row[2], "2.500e-07")
        self.assertEqual(row[4], "14.282")
        self.assertEqual(row[5], "PASS")

    def test_fail_on_force(self):
        f = [(0.1 + 2e-5, -0.2, 0.3), FORCES[1]]
        self.write(LOG, dump([FORCES[1], FORCES[0]]), eval_xyz(-100.0, f))
        row = cl.compare(self.d)
        self.assertEqual(row[3], "2.000e-05")
        self.assertEqual(row[5], "FAIL")

    def test_fail_on_energy(self):
        self.write(LOG, dump([FORCES[1], FORCES[0]]), eval_xyz(-100.00001, FORCES))
        self.assertEqual(cl.compare(self.d)[5], "FAIL")

    def test_errors(self):
        self.write(LOG, dump([FORCES[1], FORCES[0]]), eval_xyz(-100.0, FORCES, ("O", "H")))
        self.assertEqual(cl.main([self.d]), 1)                  # element order differs
        self.write(LOG.replace("PE_START", "PE"), dump(FORCES), eval_xyz(-100.0, FORCES))
        self.assertEqual(cl.main([self.d]), 1)                  # no PE_START line


if __name__ == "__main__":
    unittest.main()
