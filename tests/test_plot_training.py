"""Tests for src/plot_training.py. Parsing is stdlib; the figure test needs matplotlib
(skipped under the system python; run with mace_env: <env>/bin/python -m unittest
tests.test_plot_training)."""
import importlib.util
import json
import os
import tempfile
import unittest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src",
                   "plot_training.py")
try:
    import matplotlib  # noqa: F401
except ImportError:
    matplotlib = None


def load():
    spec = importlib.util.spec_from_file_location("plot_training", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def eval_line(epoch, loss, f=0.1, e=0.002):
    return {"loss": loss, "rmse_e_per_atom": e, "mae_e_per_atom": e / 2, "rmse_f": f,
            "mae_f": f / 2, "mode": "eval", "epoch": epoch, "head": "Default"}


def write_log(path, epochs, losses, start_eval=True):
    with open(path, "w") as fh:
        if start_eval:   # evaluation of the starting model: skipped
            fh.write(json.dumps(eval_line(None, 9.0)) + "\n")
        for ep, loss in zip(epochs, losses):
            for b in (1.0, 3.0):   # two training batches: mean 2.0
                fh.write(json.dumps({"loss": b, "mode": "opt", "epoch": ep}) + "\n")
            fh.write(json.dumps(eval_line(ep, loss, f=loss)) + "\n")


class TestPlotTraining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def chain(self):
        a = os.path.join(self.d, "m_v1_run-1_train.txt")
        b = os.path.join(self.d, "m_v2_run-1_train.txt")
        write_log(a, range(0, 3), [0.5, 0.4, 0.3])
        write_log(b, range(2, 5), [0.31, 0.2, 0.25])   # continuation retrains epoch 2
        return a, b

    def test_chain_counts_epochs_trained(self):
        rows = self.m.curves(self.chain())
        self.assertEqual([r["epochs_trained"] for r in rows], [1, 2, 3, 4, 5, 6])
        self.assertEqual([r["epoch"] for r in rows], [0, 1, 2, 2, 3, 4])
        self.assertEqual(rows[3]["run"], "m_v2_run-1")
        self.assertAlmostEqual(rows[0]["train_batch_loss"], 2.0)
        self.assertAlmostEqual(rows[0]["F_RMSE_meV_per_A"], 500.0)
        self.assertAlmostEqual(rows[0]["E_MAE_meV_per_atom"], 1.0)

    def test_summary(self):
        s = self.m.summary(self.m.curves(self.chain()))
        self.assertEqual((s[0]["best_epoch"], s[0]["longest_no_improvement"]), (2, 0))
        self.assertEqual((s[1]["best_epoch"], s[1]["longest_no_improvement"]), (3, 1))
        self.assertNotIn("F_RMSE_change_last_50", s[1])   # chain shorter than 50 epochs

    def test_gap_in_epochs_rejected(self):
        p = os.path.join(self.d, "x_train.txt")
        write_log(p, [0, 2], [0.5, 0.4])
        with self.assertRaises(self.m.CurveError):
            self.m.curves([p])

    def test_duplicate_eval_rejected(self):
        p = os.path.join(self.d, "x_train.txt")
        write_log(p, [0, 0], [0.5, 0.4])
        with self.assertRaises(self.m.CurveError):
            self.m.read_train_txt(p)

    def test_existing_outdir_refused(self):
        a, b = self.chain()
        self.assertEqual(self.m.main([self.d, a, b]), 1)

    @unittest.skipIf(matplotlib is None, "matplotlib not available (run with mace_env)")
    def test_main_writes_outputs(self):
        a, b = self.chain()
        out = os.path.join(self.d, "out")
        self.assertEqual(self.m.main([out, a, b]), 0)
        with open(os.path.join(out, "curves.tsv")) as fh:
            lines = fh.read().splitlines()
        self.assertEqual(lines[0].split("\t"), list(self.m.COLUMNS))
        self.assertEqual(len(lines), 7)
        self.assertTrue(os.path.getsize(os.path.join(out, "training.png")) > 0)


if __name__ == "__main__":
    unittest.main()
