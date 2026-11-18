"""prep_mace_train.py: wall time, flat config, checksums, run dir and refusals."""
import argparse
import hashlib
import json
import unittest

import prep_mace_train as pm
from helpers import TempRepo, run

CFG = ("# test config\nmodel: \"MACE\"\nname: \"m1\"\nfoundation_model: data/f/f.model\n"
       "train_file: data/ds/train.xyz\nvalid_file: data/ds/valid.xyz\nmax_num_epochs: 200\n"
       "model_dir: MACE_models\nrestart_latest: true\n")
FILES = {"ds/train.xyz": "t", "ds/valid.xyz": "v", "ds/test.xyz": "x", "f/f.model": "m"}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def args(**kw):
    d = dict(config="configs/mace/m.yaml", partition="gpu", exclude="", name=None,
             time="24:00:00", gpus=1, cpus=12, max_chain=2, epochs=None, env="mace_env",
             init_checkpoint=None)
    d.update(kw)
    return argparse.Namespace(**d)


class PureTest(unittest.TestCase):
    def test_parse_time(self):
        self.assertEqual(pm.parse_time("24:00:00"), 86400)
        self.assertEqual(pm.parse_time("1-00:00:00"), 86400)
        self.assertEqual(pm.parse_time("00:30:00"), 1800)
        for bad in ("24h", "00:60:00", "0:00:00", "1-2:3"):
            with self.assertRaises(pm.PrepError, msg=bad):
                pm.parse_time(bad)

    def test_flat_yaml(self):
        e = pm.read_flat_yaml(CFG, "t")
        self.assertEqual(pm.get(e, "name"), "m1")
        pm.put(e, "max_num_epochs", "2")
        self.assertIn("max_num_epochs: 2", [x[2] for x in e])
        with self.assertRaises(pm.PrepError):
            pm.put(e, "nope", "1")
        for bad in ("a: 1\n  b: 2\n", "a\n", "a: 1\na: 2\n", "a:\n"):
            with self.assertRaises(pm.PrepError, msg=repr(bad)):
                pm.read_flat_yaml(bad, "t")


class PrepareTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        r = self.t.repo
        (r / "configs" / "mace").mkdir(parents=True)
        (r / "configs" / "mace" / "m.yaml").write_text(CFG)
        (r / "configs" / "mace" / "no_restart.yaml").write_text(
            CFG.replace("restart_latest: true\n", ""))
        cont = CFG.replace('"m1"', '"m2"') + "seed: 1\ncheckpoints_dir: MACE_models\n"
        (r / "configs" / "mace" / "cont.yaml").write_text(cont)
        (r / "configs" / "mace" / "cont_norestart.yaml").write_text(
            cont.replace("restart_latest: true\n", ""))
        (r / "configs" / "mace" / "cont_nodir.yaml").write_text(
            cont.replace("checkpoints_dir: MACE_models\n", ""))
        run(["git", "add", "-A"], r)
        run(["git", "commit", "-qm", "init"], r)
        self.store = self.t.ext / "store"
        for d in ("data/ds", "data/f", "runs"):
            (self.store / d).mkdir(parents=True)
        (r / "data").symlink_to(self.store / "data")      # like the store links (gitignored)
        (r / "runs").symlink_to(self.store / "runs")
        for k, v in FILES.items():
            (self.store / "data" / k).write_text(v)
        (self.store / "data" / "ds.sha256").write_text("".join(
            "{}  {}\n".format(sha(FILES["ds/" + n]), n) for n in ("train.xyz", "valid.xyz", "test.xyz")))
        (self.store / "data" / "f" / "SHA256SUMS").write_text("{}  f.model\n".format(sha("m")))
        conda = self.t.ext / "conda.sh"
        conda.write_text("")
        self.mcfg = {"partitions": ["gpu", "gpu_dev"],
                     "python": {"conda_sh": str(conda), "envs": ["/x/envs/mace_env"]}}

    def tearDown(self):
        self.t.__exit__(None, None, None)

    def prep(self, **kw):
        return pm.prepare(self.t.repo, "testm", self.mcfg, args(**kw))

    def refused(self, **kw):
        with self.assertRaises(pm.PrepError, msg=repr(kw)):
            self.prep(**kw)

    def test_writes_run_dir(self):
        rd = self.prep(epochs=2, exclude="node1", name="smoke", time="00:30:00")
        self.assertEqual(rd.name, "smoke")
        cfg = (rd / "config.yaml").read_text()
        self.assertIn('train_file: "{}"'.format((self.store / "data/ds/train.xyz").resolve()), cfg)
        self.assertIn("max_num_epochs: 2\n", cfg)
        self.assertIn("model_dir: MACE_models\n", cfg)   # untouched keys are kept as is
        job = (rd / "job.sbatch").read_text()
        for s in ("#SBATCH -p gpu\n", "#SBATCH --exclude=node1\n", "#SBATCH -t 00:30:00\n",
                  "conda activate /x/envs/mace_env", '-f "MACE_models/m1.model"',
                  "MAXCHAIN=2", "JOBSEC=1800", "MARGIN=300", "CHAIN=${CHAIN:-0}"):
            self.assertIn(s, job)
        info = json.loads((rd / "run_info.json").read_text())
        head = run(["git", "rev-parse", "HEAD"], self.t.repo).stdout.strip()
        self.assertEqual(info["commit"], head)
        self.assertEqual(info["overrides"], {"max_num_epochs": 2})
        self.assertEqual(sorted(info["data"]), ["foundation_model", "train_file", "valid_file"])
        self.assertEqual(info["data"]["train_file"]["sha256"], sha("t"))

    def test_defaults(self):
        rd = self.prep()
        self.assertEqual(rd.name, "m1")
        job = (rd / "job.sbatch").read_text()
        self.assertNotIn("--exclude", job)
        self.assertIn("JOBSEC=86400", job)
        self.assertIn("MARGIN=900", job)
        self.assertIn("max_num_epochs: 200\n", (rd / "config.yaml").read_text())

    def test_bad_options_refused(self):
        self.refused(partition="cpu")
        self.refused(env="other")
        self.refused(max_chain=-1)
        self.refused(epochs=0)
        self.refused(name="../x")
        self.refused(time="24h")

    def test_dirty_tree_refused(self):
        (self.t.repo / "new.txt").write_text("x")
        self.refused()

    def test_checksum_mismatch_refused_even_for_unused_file(self):
        (self.store / "data" / "ds" / "test.xyz").write_text("changed")
        self.refused()

    def test_missing_checksum_list_refused(self):
        (self.store / "data" / "f" / "SHA256SUMS").unlink()
        self.refused()

    def test_file_not_in_list_refused(self):
        (self.store / "data" / "f" / "SHA256SUMS").write_text("{}  other.model\n".format(sha("m")))
        (self.store / "data" / "f" / "other.model").write_text("m")
        self.refused()

    def test_existing_run_dir_refused(self):
        self.prep(name="a")
        self.refused(name="a")

    def test_chain_needs_restart_latest(self):
        self.refused(config="configs/mace/no_restart.yaml", name="b")
        self.prep(config="configs/mace/no_restart.yaml", name="c", max_chain=0)

    def ckpt(self, name="m1_run-1_epoch-7.pt", text="ck"):
        p = self.t.ext / name
        p.write_text(text)
        return str(p)

    def test_init_checkpoint_copied_under_new_name(self):
        rd = self.prep(config="configs/mace/cont.yaml", init_checkpoint=self.ckpt())
        dest = rd / "MACE_models" / "m2_run-1_epoch-7.pt"
        self.assertEqual(dest.read_text(), "ck")
        info = json.loads((rd / "run_info.json").read_text())
        self.assertEqual(info["init_checkpoint"], {
            "source": str((self.t.ext / "m1_run-1_epoch-7.pt").resolve()),
            "sha256": sha("ck"), "path": "MACE_models/m2_run-1_epoch-7.pt", "epoch": 7})
        self.assertIsNone(json.loads((self.prep(name="plain") / "run_info.json")
                                     .read_text())["init_checkpoint"])

    def test_init_checkpoint_refusals(self):
        c = "configs/mace/cont.yaml"
        self.refused(config=c, init_checkpoint=str(self.t.ext / "missing_epoch-7.pt"))
        self.refused(config=c, init_checkpoint=self.ckpt("m1.model"))
        self.refused(config=c, init_checkpoint=self.ckpt("m1_run-1_epoch-7_swa.pt"))
        self.refused(config=c, init_checkpoint=self.ckpt("m1_run-1_epoch-200.pt"))  # >= max
        self.refused(config=c, epochs=7, init_checkpoint=self.ckpt())
        self.refused(config="configs/mace/cont_norestart.yaml", max_chain=0,
                     init_checkpoint=self.ckpt())
        self.refused(config="configs/mace/cont_nodir.yaml", init_checkpoint=self.ckpt())
        self.assertFalse((self.store / "runs" / "m2").exists())   # nothing written


if __name__ == "__main__":
    unittest.main()
