# CLAUDE.md — pb-mace

Instructions for the agent working in this repo. Personal preferences (tone, name, execution
habits) live in `~/.claude/CLAUDE.md` on each machine, not here. This file holds project
rules and conventions only. Keep it under ~160 lines; history goes to `docs/journal.md`.

## Project
- **pb-mace**: train a MACE machine-learned force field (MLFF) on an existing, already
  labelled Prussian-blue dataset; test and validate it; run MLMD with it and compare its
  RDFs with the AIMD RDFs (owner, 2026-11-17). Main MLMD object: the PB(100)/water slab
  (ADR-0015). In scope since 2026-11-25: relabelling the 1350 Na frames with Na q1 on
  neumann (ADR-0016, `docs/na-relabel.md`). Out of scope now: other dataset generation
  (new AIMD, interface-2), active learning.
- Dataset: neumann `~/prussian-blue/cubo/dataset/consolidado/` (2026-11-16): MACE extxyz
  train/valid/test split by groups, `REF_energy`/`REF_forces` (eV, eV/Å), labels qz; no
  stress/virial for Prussian blue. To SDumont from the owner's Mac (sha256: journal
  2026-11-17). Other training files on SDumont: TODO(owner): path, at the first session.
- Validation plan (owner, 2026-11-17): short MLMD runs of interface-1, cubo222 and
  cubo-puro; their RDFs compared with AIMD RDFs of the same systems, computed on neumann.
- Machines: training and MLMD on SDumont, clone and store in
  `/scratch/acmes/eudes.fileti3/projects/` (ADR-0014; purge rule unknown: keep anything
  irreplaceable elsewhere too); neumann: setup and the AIMD RDFs.
- Legacy (read-only, ADR-0008): neumann `~/prussian-blue` (owner's CP2K/AIMD work).
- Unpublished work: private repo; data and results stay on the owner's machines.
- Started from lab-template `24a7f02` (2026-11-17, `docs/new-project.md`); remote
  `template` = `~/git/lab-template.git` on neumann.

## Hard rules
- **Never fabricate** numbers, paths, versions, hyperparameters, job IDs, hashes or
  references. Unknown → `TODO(owner): <question>`, and list it in the report.
- **Fix the reading rule first** (ADR-0013). Before the output of a run whose result will
  support a claim or a comparison is analysed, the experiment doc fixes the question, the
  metric, the threshold and what counts as yes, no or inconclusive, and `docs/claims.md`
  gets a *pending* claim with that rule. A model's dataset version, split and
  hyperparameters are fixed before it is trained. The rule is never changed after the
  results are seen; a changed rule makes a new claim.
  Benchmarks, dataset generation/labelling, tests and toy jobs are exempt (still ask-first).
- **Decisions** (ADR-0013, no teach-back): the agent proposes in 2–3 lines (what and why);
  the owner answers "ok" or "approved"; the record keeps that answer and the agent's
  justification. An ADR only for general choices (physics, training or simulation
  protocol, analysis method, infrastructure); experiment choices go in the experiment doc,
  small ones in the journal entry (Decisions).
- **Ask first before:** submitting or cancelling **any** job (until per-machine limits are
  set, ADR-0005); deleting or overwriting files the agent did not create; force-push;
  `sudo` or any system-wide change; anything outside the repo. Existing work directories
  (Prussian blue, ZnCl2, AlCl3, ...) are **read-only**.
- **Secrets:** never ask for or write passwords, passphrases, tokens, VPN credentials or keys.
  Give the owner the command; the owner types it.
- **Explain commands:** git, SSH, VS Code and Claude Code commands get one line (what and
  why). Shell and Slurm: no explanation unless unusual.
- **Fair comparisons:** same model and same compute per run; validation data drawn from the
  training side only; test data never influence a choice.
- **Style:** simplest design, surgical changes, a check for every step (then run it). Show
  the diff before editing an existing file.

## Workflow
**Session loop** (one machine per session): `/start-session` (read-only recap,
fast-forward pull) → work the *Now* tasks → `/end-session` (journal, status, ledger,
results, commit, push). Skills in `.claude/skills/`; their facts come from
`python3 scripts/session_facts.py`.

**Tasks** live only in the status block (ADR-0011): *Now* (this session), *Later*
(backlog), *Waiting on owner* (blocked on the owner's decision or a fact). One line each.
A finished task leaves the block and goes to the journal entry (Done or Problems).

**Task loop** — every step has a check; run it and report its output:
1. Decision involved? Propose it in 2–3 lines; apply only after the owner's "ok"
   (ADR-0013); a general choice gets its ADR before it is applied.
2. Run that will support a claim or comparison? Copy `docs/experiment-template.md`, fix
   the reading rule and add the *pending* claim before anything runs.
3. Job? Ask first; submit from a dir under `runs/`, clean tree, commit recorded.
4. Ended? At `/end-session`: register results, apply the fixed rule to the claim, cost
   from the ledger.

## Two machines
- `origin` is a private GitHub repo (ADR-0012): pull at `/start-session`, push at
  `/end-session`; one deploy key per (repo, machine) behind an ssh alias `github-<repo>`.
  Repos created before ADR-0012 keep their bare `origin` (`~/git/<repo>.git`) until migrated.
- Scripts detect the machine from `hostname` and read `configs/machines/<machine>.yaml`
  (strict YAML subset, unknown keys rejected; `scripts/machine_config.py detect|show|validate`).
  Paths, partitions, modules, envs and cost unit live there, never hard-coded; `unknown`
  marks an unverified fact and is never replaced by a guess.
- Scripts in `scripts/` use the Python standard library only, run on Python >= 3.6
  (neumann `/usr/bin/python3` is 3.6.8) and must not rely on the active conda env
  (neumann auto-activates `deepmd_intel` in interactive shells only).
  Job scripts activate their env explicitly, from the machine YAML.
- neumann: `/home` is NFS-exported to the nodes; `/scratch` exists on the headnode only.
- SDumont: the login node limits CPU time per process (`ulimit -t 1800`); heavy interactive
  work goes to `salloc`/`srun` on a `*_dev` partition. TODO(owner): confirm usage policy.
- CP2K: never guess MPI×threads; copy the layout of the owner's benchmarked SLURM scripts.

## Conventions
- **Journal** (`docs/journal.md`): append-only, newest first, below the marker line.
  Title: `## YYYY-MM-DD — <machine> — <short title>`; fields Goal / Done (commit hashes, job
  IDs) / Results / Decisions / Problems / Next.
- **ADRs** (`docs/decisions/NNNN-title.md`): Context → Decision (who, date) → owner's
  explanation or approval + agent's check → Consequences. Never edit an accepted ADR;
  supersede it (linked both ways). Index and template: `docs/decisions/README.md`.
- **Claims** (`docs/claims.md`): status final / provisional / pending (+ "negative").
  A number not in a claim is not stated.
- **Results** (`results/<name>/`): verbatim copies + `PROVENANCE.json`, via
  `scripts/register_result.py`; never hand-edited. Legacy results enter as `legacy-*`
  (ADR-0008).
- **Cost**: one ledger per machine, `results/cost_ledger_<machine>.csv`, appended by
  `scripts/cost_ledger.py` from scheduler accounting; failed and cancelled jobs count.
  Only jobs submitted under `runs/` (or given with `--jobs`) are charged to the project
  (ADR-0005, ADR-0009, ADR-0010).
- **Runs** record the exact commit (`git rev-parse HEAD`) and refuse a dirty tree.
- **Never in git**: `data/`, `runs/`, `logs/` (gitignored; symlinks to large storage),
  extensions in `scripts/blocked_extensions.txt` (checkpoints, arrays, archives,
  datasets, trajectories), files > 1 MiB. Enforced by `.githooks/pre-commit` →
  `scripts/check_staged_files.sh`.
- Docs in English; chat with the owner in Portuguese (ADR-0006).
- Commit messages: `<type>: <summary>` (feat, fix, docs, chore, test).

## Where things live
| Question | Place |
|---|---|
| What is true now? | status block below |
| What do we do next? | status block: Now / Later / Waiting on owner |
| What happened? | `docs/journal.md` |
| Why is it built this way? | `docs/decisions/` |
| What can we state? | `docs/claims.md` |
| What is it based on? | `results/<name>/` |
| What did it cost? | `results/cost_ledger_<machine>.csv` |
| What does this word mean? | `docs/glossary.md` |
| Who said so? | `docs/references.bib` (entry only after a Crossref/arXiv check) |
| Machine facts | `configs/machines/<machine>.yaml` |
| Python envs (record only) | `envs/<machine>.environment.yml` |
| Agent permissions | `.claude/settings.json` (ask: jobs, push; deny: force-push, `rm -rf`, edits in `results/`) |

## New clone checklist
1. `git config core.hooksPath .githooks` (turns on the pre-commit hook; per clone).
2. Create the `data`, `runs`, `logs` symlinks to the machine's storage (project repos only).
3. Run the tests: `python3 -I -m unittest discover -s tests` (stdlib only).
4. `scripts/machine_config.py detect` prints this machine's name (else add/fix its YAML).

## Status
<!-- BEGIN STATUS -->
- Updated: 2026-11-27 — neumann
- State: on neumann, SDumont (`/scratch`, ADR-0014) and GitHub; `pb_mace_v2` is the MLMD model
  (validation-loss rule; LAMMPS file); main MLMD object: the PB(100)/water slab, 3×3 test
  config ready (ADR-0015; nanocube dropped); Na grid error confirmed by translation test v2
  (`results/na-translation-test-v2/`); Na protocol q1 at 700/70 (ADR-0016), on the condition
  of the q1 check (`docs/na-relabel.md`: v1 inconclusive, rule v2 fixed; `runs/na-q1-check`
  at `46ca661`, jobs 4418–4420 running since 2026-11-27 18:40, 4417 done); ID-3 MLMD on
  SDumont since 2026-11-21 (11754110–12); ID-1, ID-2, ID-3 pending; V7 in
  `pb-mace-store/manuscript/`. No final claims.
- Now (neumann):
  - q1 check: when 4418 (q9-c2000), 4419 (q1-c700) and 4420 (q1-c2000) end, `cost_ledger.py add`, then `python3 src/na_q1_check.py runs/na-q1-check` (rule v2).
  - q1 check: register (ask which files, with `q9-seed-diag`), apply the verdict to ADR-0016; if q1 SCF failures (f03, f06 so far) leave < 9 valid frames, propose the next step on q1 SCF robustness.
- Now (SDumont):
  - ID-3 MLMD: jobs 11754110 (cubo-puro), 11754111 (cubo222), 11754112 (interface-1) in `runs/mlmd-v2-*-r2`; DONE/UNSTABLE/FAIL per replica; resubmit node or wall-time failures only.
  - MLMD RDFs (`configs/rdf/mlmd_pb_mace_v2.json`), `src/rdf_compare.py`, register, apply the ID-3 rule.
  - Slab test: `prep_mlmd.py configs/mlmd/slab100_test.json --check` (ask), then the NVT (2 replicas; nsteps after the check's speed; ask).
- Later:
  - Relabel phase 1 after a "yes" (537 non-event Na frames, ~8.4k core-h): its prep, and the retrained model's reading rule before training; then phase 2 (813 event frames).
  - Slab for a paper: thicker water, slab-thickness and lateral convergence, a Na reference other than the 400/60 AIMD (ADR-0015).
  - ID-1, ID-2: test metrics in `runs/pb_mace_v{1,2}-test/` (written 2026-11-20, unlogged), register both, apply their rules; V7 `[PENDING]`s.
  - Next model: early stopping (40) < scheduler patience (50) kept the LR at 2e-4 for 400 epochs; LR decay only if the RDFs fail.
  - Na doc "Not known" items from journal 2026-11-20 (diff first); prep `grid_points()` gives 250, CP2K 256 at 1600 Ry: fix before reuse.
  - `configs/na_relabel/q1_check.json`: `seed_job_time` 02:00:00 is too short (4405 TIMEOUT; 4415 took 28:49 alone on n12): fix before reuse (diff first).
  - Into `src/` with tests: the Fe-motif coverage check (scratchpad script not kept).
  - `prep_mlmd.py --check` parses only IN_CHECK: also run the production input briefly (2026-11-21 failure).
  - `sdumont.yaml`: GROMACS modules exist; login node has 2 V100 (diff first).
  - `template` remote on SDumont once lab-template is on GitHub (ADR-0012).
- Waiting on owner:
  - Slab paper: the 2–3 central questions (agent's proposal 2026-11-25: water structure, Na⁺ distribution and desolvation, rare-event free energies vs the AIMD/PMF).
  - ID-1/ID-2: which files to register; add the Na grid-error limit to both (diff first).
  - SDumont: cost unit (ADR-0005), `/scratch` purge rule, Slurm e-mail at job end.
  - Git author name on SDumont (`fileti-fileti`) vs neumann (`Eudes Fileti`): keep or align.
  - Manuscript V7 `[CONFIRM]`s: b/TS/TSr variants, interface_aimd/longa, gate, AIMD block length, per-system std.
  - Independent test set (no test frames of cubo222 or the interface-1 AIMD): dataset generation is out of scope now.
- Last sync — neumann: 2026-11-27, end-of-session commit on top of `10f3511`
- Last sync — sdumont: 2026-11-21, end-of-session commit on top of `7fc9fb5`
<!-- END STATUS -->
