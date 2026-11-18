"""prep_mace_eval.py: run dir, recorded checksums and refusals."""
import argparse
import hashlib
import json
import unittest

from helpers import TempRepo, run
import prep_mace_eval as pe


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def args(**kw):
    d = dict(model="runs/train/m.model", configs="data/ds/test.xyz", name="m-test",
             partition="gpu_dev", exclude="", time="00:20:00", cpus=12, batch_size=2,
             env="mace_env")
    d.update(kw)
    return argparse.Namespace(**d)


class PrepEvalTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        r = self.t.repo
        (r / "README").write_text("x")
        run(["git", "add", "-A"], r)
        run(["git", "commit", "-qm", "init"], r)
        self.store = self.t.ext / "store"
        for d in ("data/ds", "runs/train"):
            (self.store / d).mkdir(parents=True)
        (r / "data").symlink_to(self.store / "data")
        (r / "runs").symlink_to(self.store / "runs")
        for n, v in (("train.xyz", "t"), ("test.xyz", "x")):
            (self.store / "data" / "ds" / n).write_text(v)
        (self.store / "data" / "ds.sha256").write_text(
            "{}  train.xyz\n{}  test.xyz\n".format(sha("t"), sha("x")))
        (self.store / "runs" / "train" / "m.model").write_text("model")
        conda = self.t.ext / "conda.sh"
        conda.write_text("")
        self.mcfg = {"partitions": ["gpu", "gpu_dev"],
                     "python": {"conda_sh": str(conda), "envs": ["/x/envs/mace_env"]}}

    def tearDown(self):
        self.t.__exit__(None, None, None)

    def prep(self, **kw):
        return pe.prepare(self.t.repo, "testm", self.mcfg, args(**kw))

    def refused(self, **kw):
        with self.assertRaises(pe.pm.PrepError, msg=repr(kw)):
            self.prep(**kw)

    def test_writes_run_dir(self):
        rd = self.prep(exclude="node1")
        job = (rd / "job.sbatch").read_text()
        test_xyz = (self.store / "data/ds/test.xyz").resolve()
        model = (self.store / "runs/train/m.model").resolve()
        for s in ("#SBATCH -p gpu_dev\n", "#SBATCH --exclude=node1\n", "#SBATCH -t 00:20:00\n",
                  "conda activate /x/envs/mace_env",
                  'mace_eval_configs --configs "{}" --model "{}" --output eval.xyz'.format(
                      test_xyz, model),
                  "--default_dtype float64 --batch_size 2", "touch DONE", "touch FAIL"):
            self.assertIn(s, job)
        info = json.loads((rd / "run_info.json").read_text())
        head = run(["git", "rev-parse", "HEAD"], self.t.repo).stdout.strip()
        self.assertEqual(info["commit"], head)
        self.assertEqual(info["model"]["sha256"], sha("model"))
        self.assertEqual(info["configs"]["sha256"], sha("x"))
        self.assertNotIn("--exclude", (self.prep(name="b") / "job.sbatch").read_text())

    def test_refusals(self):
        self.refused(partition="cpu")
        self.refused(env="other")
        self.refused(batch_size=0)
        self.refused(time="20m")
        self.refused(name="../x")
        self.refused(model="runs/train/missing.model")
        self.refused(configs="data/ds/missing.xyz")
        (self.store / "data" / "ds" / "other.xyz").write_text("o")
        self.refused(configs="data/ds/other.xyz")                  # not in the list
        (self.store / "data" / "ds" / "train.xyz").write_text("changed")
        self.refused()                                             # list does not match

    def test_dirty_tree_and_existing_dir_refused(self):
        self.prep(name="a")
        self.refused(name="a")
        (self.t.repo / "new.txt").write_text("x")
        self.refused(name="c")


if __name__ == "__main__":
    unittest.main()
