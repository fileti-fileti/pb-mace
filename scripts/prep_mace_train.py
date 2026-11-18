#!/usr/bin/env python3
"""Prepare a MACE training run: runs/<name>/ with config.yaml, job.sbatch and run_info.json.

Usage (login node, clean work tree; nothing is submitted, the command is printed):
  prep_mace_train.py CONFIG --partition P [--exclude NODES] [--name NAME] [--time T]
                     [--gpus 1] [--cpus 12] [--max-chain 2] [--epochs N] [--env mace_env]
                     [--init-checkpoint PATH]

CONFIG is a flat `mace_run_train` YAML in the repo (docs/mace-training.md). Checks:
- the machine is detected from configs/machines/ and the work tree is clean (commit recorded);
- the partition is in the machine YAML; conda_sh and the env are known there;
- every data file in the config (foundation_model, train_file, valid_file, test_file) exists,
  and every file of its checksum list (<dir>/SHA256SUMS or <dir>.sha256 beside the dir)
  matches; the run dir is new.
The copy in the run dir gets absolute data paths (and --epochs, if given). The job activates
the env explicitly, runs mace_run_train under `timeout` (wall time minus a margin) and, when
cut, resubmits itself (restart_latest) at most --max-chain times; it writes DONE or FAIL.
--init-checkpoint continues another run: its `*_epoch-N.pt` is copied into the run dir under
this config's name and seed, where MACE's restart_latest loads it (model, optimizer and
LR-scheduler state) and trains epochs N .. max_num_epochs-1; its sha256 goes to run_info.json.
Standard library only; runs on Python >= 3.6.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import machine_config as mc  # noqa: E402

DEFAULT_REPO = mc.DEFAULT_REPO
PATH_KEYS = ("foundation_model", "train_file", "valid_file", "test_file")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SUMS_RE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
CKPT_RE = re.compile(r"_epoch-(\d+)\.pt$")


class PrepError(Exception):
    pass


def parse_time(text):
    """Slurm wall time HH:MM:SS or D-HH:MM:SS -> seconds."""
    m = re.match(r"^(?:(\d+)-)?(\d{1,3}):(\d{2}):(\d{2})$", text)
    if not m or int(m.group(3)) > 59 or int(m.group(4)) > 59:
        raise PrepError("--time {!r}: expected HH:MM:SS or D-HH:MM:SS".format(text))
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    sec = ((d * 24 + h) * 60 + mi) * 60 + s
    if sec <= 0:
        raise PrepError("--time {!r}: must be positive".format(text))
    return sec


def margin_for(seconds):
    """Time left to MACE and the resubmission after `timeout` stops training."""
    return 900 if seconds > 3600 else 300


def unquote(v):
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"" else v


def read_flat_yaml(text, src):
    """Flat `key: value` lines -> list of [key, value, raw]; key None for comments/blanks."""
    out, seen = [], set()
    for n, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            out.append([None, None, raw])
            continue
        if raw[0] in " \t" or ":" not in s:
            raise PrepError("{}:{}: expected a flat 'key: value' line".format(src, n))
        k, v = s.split(":", 1)
        k, v = k.strip(), v.split(" #")[0].strip()
        if not k or not v:
            raise PrepError("{}:{}: empty key or value".format(src, n))
        if k in seen:
            raise PrepError("{}:{}: duplicate key {!r}".format(src, n, k))
        seen.add(k)
        out.append([k, v, raw])
    return out


def get(entries, key):
    for k, v, _ in entries:
        if k == key:
            return unquote(v)
    return None


def put(entries, key, value):
    for e in entries:
        if e[0] == key:
            e[1], e[2] = value, "{}: {}".format(key, value)
            return
    raise PrepError("config has no {!r} to override".format(key))


def sha256(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sums_file(path):
    d = path.parent
    cands = [d / "SHA256SUMS", d.parent / (d.name + ".sha256")]
    for c in cands:
        if c.is_file():
            return c
    raise PrepError("{}: no checksum list ({})".format(path, " or ".join(map(str, cands))))


def verify_sums(sf, base):
    """Check every file listed in sf (names relative to base) -> {abs path: sha256}."""
    listed = {}
    for n, line in enumerate(sf.read_text().splitlines(), 1):
        if not line.strip():
            continue
        m = SUMS_RE.match(line)
        if not m:
            raise PrepError("{}:{}: not a sha256sum line".format(sf, n))
        listed[m.group(2)] = m.group(1)
    if not listed:
        raise PrepError("{}: empty checksum list".format(sf))
    ok = {}
    for name, want in sorted(listed.items()):
        p = base / name
        if not p.is_file():
            raise PrepError("{}: listed in {} but missing".format(p, sf))
        got = sha256(p)
        if got != want:
            raise PrepError("{}: sha256 {} != {} ({})".format(p, got, want, sf))
        ok[str(p)] = got
    return ok


def init_checkpoint_plan(entries, src):
    """--init-checkpoint -> {source, sha256, path (in the run dir), epoch}.

    MACE's restart_latest loads the highest `<name>_run-<seed>_epoch-N.pt` in checkpoints_dir
    and starts at epoch N, so the copy must carry this config's name and seed.
    """
    src = Path(src).resolve()
    if not src.is_file():
        raise PrepError("--init-checkpoint {}: no such file".format(src))
    m = CKPT_RE.search(src.name)
    if not m:
        raise PrepError("--init-checkpoint {}: expected a MACE '*_epoch-N.pt'".format(src.name))
    if (get(entries, "restart_latest") or "").lower() != "true":
        raise PrepError("--init-checkpoint needs 'restart_latest: true' in the config")
    ckdir, seed, maxep = (get(entries, k) for k in ("checkpoints_dir", "seed", "max_num_epochs"))
    if not ckdir or not seed or not maxep:
        raise PrepError("--init-checkpoint needs 'checkpoints_dir', 'seed' and 'max_num_epochs'")
    if Path(ckdir).is_absolute() or ".." in Path(ckdir).parts:
        raise PrepError("checkpoints_dir {!r}: must be inside the run dir".format(ckdir))
    epoch = int(m.group(1))
    if not seed.isdigit() or not maxep.isdigit() or int(maxep) <= epoch:
        raise PrepError("--init-checkpoint epoch {}: needs integer seed and max_num_epochs > {}"
                        .format(epoch, epoch))
    path = "{}/{}_run-{}_epoch-{}.pt".format(ckdir.rstrip("/"), get(entries, "name"), seed, epoch)
    return {"source": str(src), "sha256": sha256(src), "path": path, "epoch": epoch}


def git(repo, *args):
    p = subprocess.run(["git"] + list(args), cwd=str(repo), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    if p.returncode != 0:
        raise PrepError("git {}: {}".format(" ".join(args), p.stderr.strip()))
    return p.stdout


def find_env(mcfg, env):
    hits = [e for e in mcfg["python"]["envs"]
            if e == env or os.path.basename(e.rstrip("/")) == env]
    if len(hits) != 1:
        raise PrepError("env {!r}: {} matches in the machine YAML python.envs".format(env, len(hits)))
    return hits[0]


SBATCH = """#!/bin/bash
#SBATCH -J {name}
#SBATCH -p {partition}
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:{gpus}
#SBATCH -c {cpus}
#SBATCH -t {time}
{exclude}#SBATCH -o slurm-%j.out
# Generated by scripts/prep_mace_train.py at commit {commit}; re-run it instead of editing.
RUN={run}
cd "$RUN" || exit 1
CHAIN=${{CHAIN:-0}}
MAXCHAIN={max_chain}
JOBSEC={jobsec}
MARGIN={margin}
echo "job=$SLURM_JOB_ID chain=$CHAIN host=$(hostname) start=$(date -Iseconds)"
source {conda_sh} || exit 1
conda activate {env} || exit 1
echo "mace_run_train=$(command -v mace_run_train)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 60 >> gpu_usage.log &
MON=$!
timeout --kill-after=120 $((JOBSEC - MARGIN - SECONDS)) mace_run_train --config config.yaml
rc=$?
kill $MON 2>/dev/null
echo "mace_run_train rc=$rc end=$(date -Iseconds)"
if [ $rc -eq 0 ] && [ -f "{final_model}" ]; then
  touch DONE; exit 0
fi
if {{ [ $rc -eq 124 ] || [ $rc -eq 137 ]; }} && [ $CHAIN -lt $MAXCHAIN ]; then
  echo "wall time reached: resubmitting (chain $((CHAIN + 1)) of $MAXCHAIN)"
  sbatch --chdir="$RUN" --export=ALL,CHAIN=$((CHAIN + 1)) "$RUN/job.sbatch" && exit 0
fi
touch FAIL; exit 1
"""


def prepare(repo, machine, mcfg, a, now=None):
    repo = Path(repo).resolve()
    cfg_path = Path(a.config)
    cfg_path = (cfg_path if cfg_path.is_absolute() else repo / cfg_path).resolve()
    if not cfg_path.is_file():
        raise PrepError("{}: no such config".format(cfg_path))
    if git(repo, "status", "--porcelain").strip():
        raise PrepError("work tree not clean: commit first (runs record their commit)")
    commit = git(repo, "rev-parse", "HEAD").strip()

    if a.partition not in mcfg["partitions"]:
        raise PrepError("partition {!r} not in the {} YAML".format(a.partition, machine))
    conda_sh = mcfg["python"]["conda_sh"]
    if conda_sh == mc.UNKNOWN or not Path(conda_sh).is_file():
        raise PrepError("python.conda_sh {!r}: unknown or missing".format(conda_sh))
    env = find_env(mcfg, a.env)
    for opt in ("gpus", "cpus"):
        if getattr(a, opt) < 1:
            raise PrepError("--{} must be >= 1".format(opt))
    if a.max_chain < 0:
        raise PrepError("--max-chain must be >= 0")
    jobsec = parse_time(a.time)

    entries = read_flat_yaml(cfg_path.read_text(), str(cfg_path))
    mname, model_dir = get(entries, "name"), get(entries, "model_dir")
    if not mname or not model_dir:
        raise PrepError("config needs 'name' and 'model_dir'")
    if a.max_chain > 0 and (get(entries, "restart_latest") or "").lower() != "true":
        raise PrepError("--max-chain > 0 needs 'restart_latest: true' in the config")
    if a.epochs is not None:
        if a.epochs < 1:
            raise PrepError("--epochs must be >= 1")
        put(entries, "max_num_epochs", str(a.epochs))
    init = init_checkpoint_plan(entries, a.init_checkpoint) if a.init_checkpoint else None

    data, checked = {}, {}
    for key in PATH_KEYS:
        v = get(entries, key)
        if v is None:
            continue
        p = Path(v) if Path(v).is_absolute() else repo / v
        if not p.is_file():
            raise PrepError("{}: {}: no such file".format(key, p))
        p = p.resolve()
        sf = sums_file(p)
        if str(sf) not in checked:
            checked[str(sf)] = verify_sums(sf, p.parent)
        if str(p) not in checked[str(sf)]:
            raise PrepError("{}: {} not listed in {}".format(key, p, sf))
        put(entries, key, '"{}"'.format(p))
        data[key] = {"path": str(p), "sha256": checked[str(sf)][str(p)], "list": str(sf)}

    name = a.name or mname
    if not NAME_RE.match(name):
        raise PrepError("run name {!r}: use letters, digits, '.', '_' or '-'".format(name))
    runs = repo / "runs"
    if not runs.is_dir():
        raise PrepError("{}: no runs/ dir or link".format(runs))
    run = runs / name
    if run.exists():
        raise PrepError("{}: run dir exists; pick another --name".format(run))

    rel_cfg = str(cfg_path.relative_to(repo)) if repo in cfg_path.parents else str(cfg_path)
    header = "# Generated from {} at commit {} by scripts/prep_mace_train.py.\n".format(
        rel_cfg, commit)
    final_model = "{}/{}.model".format(model_dir.rstrip("/"), mname)
    sbatch = SBATCH.format(
        name=name, partition=a.partition, gpus=a.gpus, cpus=a.cpus, time=a.time,
        exclude="#SBATCH --exclude={}\n".format(a.exclude) if a.exclude else "",
        commit=commit, run=run, max_chain=a.max_chain, jobsec=jobsec,
        margin=margin_for(jobsec), conda_sh=conda_sh, env=env, final_model=final_model)
    info = {
        "created": (now or datetime.datetime.now()).isoformat(timespec="seconds"),
        "machine": machine, "host": socket.gethostname(), "commit": commit,
        "config": rel_cfg, "config_sha256": sha256(cfg_path),
        "overrides": {"max_num_epochs": a.epochs} if a.epochs is not None else {},
        "data": data, "checksum_lists": sorted(checked),
        "slurm": {"partition": a.partition, "exclude": a.exclude, "gpus": a.gpus,
                  "cpus": a.cpus, "time": a.time, "max_chain": a.max_chain},
        "conda_sh": conda_sh, "env": env, "final_model": final_model,
        "init_checkpoint": init,
    }
    run.mkdir()
    if init:   # before job.sbatch: a failed copy leaves no job to submit
        dest = run / init["path"]
        dest.parent.mkdir(parents=True)
        shutil.copyfile(init["source"], str(dest))
        if sha256(dest) != init["sha256"]:
            raise PrepError("{}: copy does not match {}".format(dest, init["source"]))
    (run / "config.yaml").write_text(header + "\n".join(e[2] for e in entries) + "\n")
    (run / "job.sbatch").write_text(sbatch)
    (run / "run_info.json").write_text(json.dumps(info, indent=2) + "\n")
    return run


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=str(DEFAULT_REPO), help=argparse.SUPPRESS)
    ap.add_argument("config")
    ap.add_argument("--partition", required=True)
    ap.add_argument("--exclude", default="")
    ap.add_argument("--name")
    ap.add_argument("--time", default="24:00:00")
    ap.add_argument("--gpus", type=int, default=1)
    ap.add_argument("--cpus", type=int, default=12)
    ap.add_argument("--max-chain", type=int, default=2)
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--env", default="mace_env")
    ap.add_argument("--init-checkpoint")
    a = ap.parse_args(argv)
    try:
        machine = mc.detect(a.repo)
        run = prepare(a.repo, machine, mc.load(machine, a.repo), a)
    except (PrepError, mc.ConfigError) as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1
    print("prepared {}".format(run))
    print("submit (ask first): cd {} && sbatch job.sbatch".format(run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
