"""prep_mlmd.py: start frame from an extxyz set, Fe2/Fe3 from geometry, LAMMPS data and
inputs, replica job, check job, recorded checksums, refusals."""
import argparse
import hashlib
import json
import unittest

from helpers import TempRepo, run
import prep_mlmd as pl

LAT = 'Lattice="10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0" Properties=species:S:1:pos:R:3:REF_forces:R:3'
# frame 0: other config_type; frame 1: the start (Fe at 0.5 bonded to C across the boundary
# at 9.0 -> Fe2; Fe at 5.0 bonded to N only -> Fe3; Na at -0.5 is wrapped to 9.5)
TRAIN = (
    "2\n{} REF_energy=-1.0 config_type=agua grupo=agua:0 pbc=\"T T T\"\n"
    "O 1.0 1.0 1.0 0 0 0\nH 1.5 1.0 1.0 0 0 0\n"
    "5\n{} REF_energy=-2.0 config_type=box grupo=box:3 pbc=\"T T T\"\n"
    "Fe 0.5 0.5 0.5 0 0 0\nC 9.0 0.5 0.5 0 0 0\nFe 5.0 5.0 5.0 0 0 0\nN 7.0 5.0 5.0 0 0 0\n"
    "Na -0.5 11.0 5.0 0 0 0\n"
    "5\n{} REF_energy=-2.0 config_type=box grupo=box:3 pbc=\"T T T\"\n"
    "Fe 9.9 9.9 9.9 0 0 0\nC 9.9 9.9 9.9 0 0 0\nFe 9.9 9.9 9.9 0 0 0\nN 9.9 9.9 9.9 0 0 0\n"
    "Na 9.9 9.9 9.9 0 0 0\n").format(LAT, LAT, LAT)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def args(**kw):
    d = dict(config="configs/mlmd/t.json", system="box", check=False, name="md-box",
             partition="gpu", exclude="", time="1-00:00:00", cpus=6, env="mace_env")
    d.update(kw)
    return argparse.Namespace(**d)


class PrepMlmdTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        r, ext = self.t.repo, self.t.ext
        self.store = ext / "store"
        (self.store / "data" / "ds").mkdir(parents=True)
        (self.store / "runs" / "train").mkdir(parents=True)
        (r / "data").symlink_to(self.store / "data")
        (r / "runs").symlink_to(self.store / "runs")
        self.write_train(TRAIN)
        (self.store / "runs" / "train" / "m.model").write_text("model")
        (self.store / "runs" / "train" / "m.model-lammps.pt").write_text("lammps model")
        for d in ("lib1", "lib2"):
            (ext / d).mkdir()
        self.lmp = ext / "lmp"
        self.lmp.write_text("")
        conda = ext / "conda.sh"
        conda.write_text("")
        self.cfg = {
            "description": "test", "model": "runs/train/m.model-lammps.pt",
            "model_source": "runs/train/m.model",
            "lammps_ld_library_path": [str(ext / "lib1"), str(ext / "lib2")],
            "temperature_K": 350.0, "tdamp_fs": 100.0, "replicas": 3, "seed_base": 1000,
            "bench_steps": 200,
            "masses": {"Fe": 55.845, "C": 12.011, "N": 14.007, "Na": 22.98976928,
                       "O": 15.999, "H": 2.0141},
            "systems": {"box": {"start": "data/ds/train.xyz", "config_type": "box",
                                "fe2_fe3": [1, 1], "cell": [10.0, 10.0, 10.0],
                                "dt_fs": 1.5, "nsteps": 70, "dump_every": 7}}}
        self.write_cfg()
        self.mcfg = {"partitions": ["gpu", "gpu_dev"], "modules": {"lammps": str(self.lmp)},
                     "python": {"conda_sh": str(conda), "envs": ["/x/envs/mace_env"]}}

    def write_train(self, text):
        (self.store / "data" / "ds" / "train.xyz").write_text(text)
        (self.store / "data" / "ds.sha256").write_text("{}  train.xyz\n".format(sha(text)))

    def write_cfg(self):
        r = self.t.repo
        (r / "configs" / "mlmd").mkdir(parents=True, exist_ok=True)
        (r / "configs" / "mlmd" / "t.json").write_text(json.dumps(self.cfg))
        run(["git", "add", "-A"], r)
        run(["git", "commit", "-qm", "cfg", "--allow-empty"], r)

    def tearDown(self):
        self.t.__exit__(None, None, None)

    def prep(self, **kw):
        return pl.prepare(self.t.repo, "testm", self.mcfg, args(**kw), ldd=False)

    def refused(self, **kw):
        with self.assertRaises(pl.pm.PrepError, msg=repr(kw)):
            self.prep(**kw)

    def test_production_run_dir(self):
        rd = self.prep(exclude="node1")
        data = (rd / "start.data").read_text().splitlines()
        self.assertIn("5 atoms", data)
        self.assertIn("4 atom types", data)            # Fe C N Na, in ELEMENT_ORDER
        self.assertIn("4 22.98976928  # Na", data)
        atoms = data[data.index("Atoms # atomic") + 2:]
        self.assertEqual(atoms[4], "5 4 9.50000000 1.00000000 5.00000000")   # wrapped Na
        kinds = (rd / "kinds.inc").read_text().splitlines()
        self.assertEqual([l.split()[0] for l in kinds[2:7]], ["Fe2", "C", "Fe3", "N", "Na"])
        self.assertEqual(kinds[-1], "&END COORD")
        inp = (rd / "in.lmp").read_text()
        model = (self.store / "runs/train/m.model-lammps.pt").resolve()
        for s in ("read_data       ../start.data", "pair_coeff      * * {} Fe C N Na".format(model),
                  "timestep        0.001500", "velocity        all create 350.0 ${SEED} mom yes rot no",
                  "fix             nvt all nvt temp 350.0 350.0 0.1",
                  "dump            trj all xyz 7 traj.xyz",
                  "dump_modify     trj element Fe C N Na sort id", "run             70"):
            self.assertIn(s, inp)
        self.assertEqual(sorted(p.name for p in rd.iterdir() if p.is_dir()), ["rep1", "rep2", "rep3"])
        job = (rd / "job.sbatch").read_text()
        for s in ("#SBATCH -p gpu\n", "#SBATCH --exclude=node1\n", "#SBATCH -t 1-00:00:00\n",
                  "export LD_LIBRARY_PATH={}:{}".format(*self.cfg["lammps_ld_library_path"]),
                  "LMP={}".format(self.lmp), "seq 1 3", "seed=$(( 1000 + k ))",
                  "-var SEED $seed", "touch DONE"):
            self.assertIn(s, job)
        info = json.loads((rd / "run_info.json").read_text())
        head = run(["git", "rev-parse", "HEAD"], self.t.repo).stdout.strip()
        self.assertEqual(info["commit"], head)
        self.assertEqual(info["model"]["sha256"], sha("lammps model"))
        self.assertEqual(info["model_source"]["sha256"], sha("model"))
        st = info["systems"]["box"]["start"]
        self.assertEqual((st["sha256"], st["frame"], st["group"]), (sha(TRAIN), 1, "box:3"))
        self.assertEqual(info["systems"]["box"]["fe2_fe3"], [1, 1])
        self.assertEqual(info["seeds"], [1001, 1002, 1003])

    def test_check_run_dir(self):
        rd = self.prep(check=True, system=None, name="chk", partition="gpu_dev", time="00:20:00")
        d = rd / "box"
        ext = (d / "start.extxyz").read_text().splitlines()
        self.assertEqual(ext[0], "5")
        self.assertIn('Lattice="10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0"', ext[1])
        self.assertEqual(ext[6], "Na 9.50000000 1.00000000 5.00000000")
        inp = (d / "in_check.lmp").read_text()
        for s in ("read_data       start.data", "run             0", 'print           "PE_START',
                  "dump            frc all custom 1 forces.dump id element fx fy fz",
                  "run             200"):
            self.assertIn(s, inp)
        job = (rd / "job.sbatch").read_text()
        src = (self.store / "runs/train/m.model").resolve()
        for s in ("for s in box; do", '--model "{}"'.format(src), "compare_lammps_eval.py",
                  "check.tsv"):
            self.assertIn(s, job)

    def test_refusals(self):
        self.refused(partition="cpu")
        self.refused(env="other")
        self.refused(system="other")
        self.refused(name="../x")
        self.refused(time="20m")

    def test_data_checks(self):
        (self.store / "data" / "ds" / "train.xyz").write_text(TRAIN + "\n")
        self.refused()                                       # checksum list does not match
        self.write_train(TRAIN.replace("C 9.0 0.5", "C 7.0 0.5"))
        self.refused()                                       # C too far: Fe2/Fe3 = 0/2
        self.write_train(TRAIN.replace("10.0 0.0 0.0 0.0 10.0", "11.0 0.0 0.0 0.0 10.0"))
        self.refused()                                       # cell differs
        self.write_train(TRAIN.replace("config_type=box", "config_type=other"))
        self.refused()                                       # no frame of the config_type

    def test_config_checks(self):
        self.cfg["replicas"] = 1
        self.write_cfg()
        self.refused()
        self.cfg["replicas"] = 3
        self.cfg["extra"] = 1
        self.write_cfg()
        self.refused()

    def test_dirty_tree_and_existing_dir_refused(self):
        self.prep(name="a")
        self.refused(name="a")
        (self.t.repo / "new.txt").write_text("x")
        self.refused(name="c")


if __name__ == "__main__":
    unittest.main()
