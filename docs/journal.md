# Journal

Append-only. Newest entry first, directly below the marker line.
Title: `## YYYY-MM-DD — <machine> — <short title>`.

```
## YYYY-MM-DD — <machine> — <short title>
- Goal: ...
- Done: ... (each item with its commit hash and job ID)
- Results: the conclusion and the few numbers that carry it, linked to the doc
- Decisions: ADRs added or changed (teach-back or owner approval recorded there)
- Problems: what failed, with job IDs and error lines (root cause)
- Next: concrete steps
```

<!-- NEW ENTRIES BELOW -->
## 2026-11-19 — sdumont — v2 chosen, Na label grid error, MLMD vs AIMD RDF set up
- Goal: close the 2026-11-18 gap, read the convergence and the validation parity of the
  models, decide whether the MLMD can start, and set up the MLMD vs AIMD RDF test.
- Done:
  - 2026-11-18 (no end-of-session that day; rebuilt from git, sacct and run dirs):
    `f6f2e85` pb_mace_v2 continuation of v1 and claim ID-2 pending; `7efbb64` ID-1 metrics
    script (`src/mace_errors.py`) and eval prep. Jobs 11745412 `pb_mace_v1` COMPLETED
    (44 945 s), 11747460 `pb_mace_v2` COMPLETED (45 528 s), 11747493 `pb_mace_v1-test`
    COMPLETED (164 s; `runs/pb_mace_v1-test/errors/` written, not registered).
  - `bb775db` glossary terms of 2026-11-18; `c654e6f` `src/plot_training.py` and
    `src/plot_parity.py` (+ tests; parity checked on a synthetic set).
  - Jobs 11750727 `pb_mace_v2-valid` (194 s) and 11750733 `pb_mace_v2-test` (23 s),
    COMPLETED, in turn (`sequana_gpu_dev`: MaxSubmitJobs 1 per user). Validation errors and
    parity in `runs/pb_mace_v2-valid/{errors,parity}/`; the v2 test output is not analysed.
  - `mace_create_lammps_model runs/pb_mace_v2/MACE_models/pb_mace_v2.model --dtype float64
    --head Default` (login node, 12 s): `pb_mace_v2.model-lammps.pt`, sha256 `1bec5180…`
    (full in claim ID-3).
  - `3f1007c` `scripts/prep_mlmd.py`, `src/compare_lammps_eval.py`, `src/rdf_compare.py`,
    `src/rdf.py` (LAMMPS xyz, per-block curves), configs `configs/mlmd/pb_mace_v2_rdf.json`
    and `configs/rdf/mlmd_pb_mace_v2.json` (+ tests). `e44ecab` MLMD protocol and reading
    rule in `docs/rdf-mlmd-vs-aimd.md`, claim ID-3 pending.
  - Job 11750830 `mlmd-v2-check` (`runs/mlmd-v2-check`, commit `e44ecab`), COMPLETED in
    299 s: LAMMPS vs `mace_eval_configs` on the 3 start frames and a 200-step benchmark.
  - Ledger: 6 rows added (11745412, 11747460, 11747493, 11750727, 11750733, 11750830); 0
    jobs outside the project skipped.
- Results (monitoring, not claims):
  - Convergence (`src/plot_training.py` on the v1 and v2 `_train.txt`): v1 saved its last
    epoch (199, validation loss 0.3002); v2 saved epoch 390 of 199–398 (0.2171), so v2 is
    the MLMD model by the rule of `docs/mace-training.md`. Validation force RMSE 85.3, 79.1,
    76.5, 74.4, 73.5 meV/Å at 200, 250, 300, 350, 392 epochs trained. Learning rate 2e-4
    throughout (scheduler state in the checkpoints of epochs 199 and 390).
  - v2 on `valid.xyz` (`runs/pb_mace_v2-valid/errors/errors.tsv`): forces 73.5 meV/Å RMSE
    (47.2 without Na atoms), energy 2.06 meV/atom; per element H 19.3, C 41.4, O 41.5,
    N 73.7, Fe 89.2, Na 390.1 meV/Å; slope of prediction on reference ≥ 0.99 for all but
    Na (0.18, r 0.41). Energy errors are a constant offset per composition (RMSE ≈ MAE per
    config_type): no effect at fixed composition.
  - Na: the reference forces carry a CP2K grid (egg-box) error (numbers and checks in
    `docs/rdf-mlmd-vs-aimd.md`, limit 7): the net reference force of Na frames equals the
    sum of the Na residuals; the Na residual is periodic in the absolute position with the
    700 Ry grid (best fit at N = 162, 576, 324 on all 9 axes). The 400/60 AIMD Na positions
    are non-uniform modulo the 400 Ry grid. Scripts in the session scratchpad, not kept.
  - AIMD timestep from the registered trajectory headers: 1.5 fs (cubo-puro), 1.0 fs
    (cubo222, interface-1). Fe2/Fe3 from geometry equals the AIMD counts (4/4, 30/32, 8/8).
  - Check (`runs/mlmd-v2-check/check.tsv`): LAMMPS = `mace_eval_configs` on the 3 start
    frames, PASS (|ΔE|/N ≤ 1.7e-12 eV/atom, max |ΔF| 5.0e-9 eV/Å), cells < 12 Å and the Na
    map included. Timesteps/s on 1 V100: cubo-puro 17.955, cubo222 4.871, interface-1 7.013.
    Production estimate (5 replicas × nsteps / rate + start-up from the check logs):
    cubo-puro 0.69 h, cubo222 1.57 h, interface-1 1.09 h; 3.35 GPU-h in all.
- Decisions (owner):
  - "ok, vamos seguir com o teste de RDF"; "ok, no rascunho": MLMD protocol and reading
    rule of `docs/rdf-mlmd-vs-aimd.md` (agent's proposal, reasons in the doc).
  - "vamos prosseguir sem as trajetorias da neumann…": start frame from `train.xyz`,
    Fe2/Fe3 from geometry, σ from the replicas only; "ok, faça tudo e estime a duracao do
    teste" (before any MLMD run).
  - v2 for the MLMD; no LR-decay stage now (agent's recommendation: the validation-loss
    plateau is largely the Na label floor). Test outputs not used for any choice.
- Problems:
  - The 2026-11-18 session ended without `/end-session` (journal, status, ledger, push).
  - Agent's errors, corrected before approval: a g1 verdict in the first RDF rule (twice
    the AIMD block error exceeds 10 % of g1 in 9 of 26 pairs); the claim that the AIMD Na
    pairs may be biased (the grid ripple averages out on the g(r) scale; argument, not a
    test). At the session start the agent printed the first lines of
    `runs/pb_mace_v1-test/errors/errors.tsv` (format check); not used.
  - LAMMPS build: no `fix temp/csvr` (Nosé–Hoover instead of the AIMD's CSVR); `lmp` needs
    `libcudart.so.11.0` from `shared/cuda-links/cuda-11.4` (legacy jobs inherited it from
    the login shell; now explicit in the config, checked with `ldd`).
  - Owner's shell: `rm` is `rm -i` (a command waited on the prompt and was stopped).
- Next: the 3 production jobs (ask first; wall time about twice the estimate), MLMD RDFs,
  `src/rdf_compare.py`, register, claim ID-3.
  Owner: ID-1/ID-2 registration and the Na limit for them; Na basis/pseudopotential.

## 2026-11-17 — sdumont — Training monitoring, manuscript V7
- Goal: follow the training of `pb_mace_v1` (job 11745412) and document the training in
  the owner's manuscript (Methodology and SI), version 7, before the chat is lost.
- Done:
  - Job 11745412 running on sdumont8019 (22 epochs at 13:15, 224 s per epoch); no job
    submitted or ended since `d530e0d`; ledger: 0 rows added.
  - `d0a93db` claim ID-1 Limits: test split coverage per config_type (below), added
    before any test evaluation.
  - Manuscript V7: the owner copied `manuscript-v6.docx` from the Mac (scp) to
    `/scratch/acmes/eudes.fileti3/projects/pb-mace-store/manuscript/` (outside git, like
    the V7). V7 built there by editing `word/document.xml` of V6 (stdlib script in the
    session scratchpad, not kept): header; Section 3.6 (new Table 6: frames per
    config_type and split, groups); Section 4 with 4.1–4.5 (training data; architecture
    from the log; E0s; new Table 7; compute and duration; convergence control; results
    `[PENDING]`); Section 5, 5.1, 8 and Table 10 corrected. sha256:
    ```
    b88e04ee54d576c10bfa8a037fbc7035c4db2be3febfeeb42c04c833de7ede75  manuscript-v6.docx
    da743462b4bd0ebd1cf85b931b06cf1dfa68b4f46a524a9a324e9f32f09c648d  manuscript-v7.docx
    ```
    Checked: every part well-formed XML, same parts as V6. Not rendered nor
    schema-validated (no LibreOffice, pandoc, lxml or defusedxml on SDumont): the owner
    opens it in Word.
- Results (monitoring, not a claim):
  - Training log: `Using heads: ['Default']`; architecture from the foundation model:
    hidden irreps 128x0e, 2 layers, correlation 3, l ≤ 3, r_max 6.0 Å; 255 400 optimizer
    steps for 200 epochs; first 7 epochs 223 s each → about 12.4 h for 200 epochs.
  - Convergence speed of the validation force RMSE over the same window of optimizer steps
    (about 1.2k–6.5k), against the legacy pb_t2A2 log (A2): −1.35 % per 1000 steps vs
    −0.72 % (−4.6 % vs −2.1 % per 10 min). Different validation sets and frame sizes:
    describes the training runs, not the quality of the models.
  - `consolidado/` split (`frames.tsv`): 208 groups (173 train, 23 valid, 12 test). The
    test split has one group (11–20 frames) for 12 of the 20 config_types and none for
    cubo222, interface_aimd, interface_longa, vacancia_P1 and the interface TS windows.
- Decisions (owner: "OK"):
  - Manuscript V7 scope: training sections 4.1–4.5 plus the corrections of V6 that
    contradict the training (E0s, test independence, 300 → 200 epochs, per-atom energy
    metric, stress labels); other sections untouched.
  - Not in V7: early-epoch RMSE (monitoring) and the comparison with A2 (V6 reports no A2
    numbers; different validation sets). Computational numbers only.
  - Manuscript files in `pb-mace-store/manuscript/`, outside git; the owner keeps the copy
    on the Mac (`/scratch` purge rule unknown).
  - ID-1 Limits extended with the test coverage (owner: "OK"), before the result.
- Problems:
  - The `pt_head` concern of the previous entry was wrong: `skip_evaluate_heads='pt_head'`
    is a default option; the model has one head (`Default`).
  - Learning rate: MACE's `ReduceLROnPlateau` (factor 0.8, patience 50, relative threshold
    1e-4) has a longer patience than early stopping (40), so the learning rate stays at
    2e-4 for most or all of the run; the agent had told the owner it "starts falling after
    50 epochs". Same settings as pb_t2A2 (its log not checked). The training log does not
    record the learning rate. Not changed for this model.
  - The previous entry's split rule "20 consecutive AIMD frames" does not fit
    `interface_aimd` (29 frames in one group); the AIMD block length is unknown (V7
    `[CONFIRM]`). Event groups match the windows of V6 Table 5 (W1 12, W2v 12, P1 8).
  - Owner's shell: `cp` is `cp -i` (a background command waited on a prompt and was
    stopped); `rm -rf` is denied by the project settings.
  - V7 sections outside the agreed scope are now stale (Table 5 still "planned" for W4a/b
    and N3, which are in the dataset; 3.1 and 3.5 status lines).
- Next: next SDumont session: job 11745412 (DONE or FAIL, ledger), then the ID-1 metrics
  script and the test evaluation. Owner: open V7 in Word and answer its new `[CONFIRM]`s
  (b/TS/TSr variants and interface_aimd/longa; gate of all frames; AIMD block length;
  per-system energy std as a separate analysis).

## 2026-11-17 — sdumont — Setup, smoke run, MACE training submitted
- Goal: set up the SDumont clone (status Now), fix the MACE training design and start the
  training of `pb_mace_v1`.
- Two agent sessions on SDumont today. The first (clone 09:42, `5936029` 10:22, smoke run
  dir 10:23) ended without `/end-session` (cause unknown); its items below come from git,
  the reflog, file times and the docs it wrote. What those do not record is unknown.
- Done (first session):
  - Clone from GitHub over the alias `github-pb-mace` into
    `/scratch/acmes/eudes.fileti3/projects/pb-mace` (ADR-0014); deploy key fingerprint
    unknown (not recorded); `core.hooksPath .githooks`; store
    `/scratch/acmes/eudes.fileti3/projects/pb-mace-store/{data,runs,logs}` + symlinks.
  - `data/consolidado/` from the owner's Mac; `data/consolidado.sha256` = the sha256 list
    of the 2026-11-17 neumann entry. `data/foundation/mace_mp_small.model` copied from
    `zncl2/mace_sr/training/` (`SOURCE.txt`, `SHA256SUMS`).
  - Legacy training setup used as the starting point: `pb_t2A2` in
    `/scratch/acmes/eudes.fileti3/projects/pb/treino_v1/` (read-only, ADR-0008;
    `docs/mace-training.md`).
  - `5936029` MACE training setup: `docs/mace-training.md` (design and reading rule fixed
    with the owner), `configs/mace/pb_mace_v1.yaml`, `scripts/prep_mace_train.py` + tests,
    claim ID-1 pending, `sdumont.yaml` (`conda_sh`, LAMMPS+MACE build, GPU partitions,
    `sdumont8042` exclusion).
  - `runs/pb_mace_v1-smoke/` prepared at `5936029` (30 min on `sequana_gpu_dev`).
- Done (this session):
  - Start checks: `consolidado/` sha256 6/6 OK, foundation OK; `detect` → sdumont;
    Python 3.10.20; 68 tests OK.
  - `54cba16` the first session's uncommitted doc edit (E0s composition check, time estimate).
  - `00ba18b` `envs/sdumont.environment.yml`: record of `mace_env` (Python 3.10.20,
    mace-torch 0.3.15, torch 2.2.0+cu121).
  - Smoke: job 11745176 (`runs/pb_mace_v1-smoke/`) cancelled while pending (Problems);
    `7ca6665` doc step 3 at 20 min; job 11745195 (`runs/pb_mace_v1-smoke2/`, prepared at
    `7ca6665`) on sdumont8093, 902 s.
  - `5812181` ledger: 2 rows (11745176, 11745195), cost unknown (unit unknown).
  - Training: `runs/pb_mace_v1/` prepared at `5812181` (`sequana_gpu`, 1 GPU, `-c 12`,
    24 h, max chain 2, `--exclude=sdumont8042`); job 11745412 running on sdumont8019 since
    2026-11-17T11:49:25.
  - `22cd989` `sdumont.yaml`: max wall time per job per partition (sacctmgr), GPU model.
- Results (smoke run, toy; no claim):
  - `conda_sh` and `mace_env` work on a compute node; the config with Na runs (atomic
    numbers [1, 6, 7, 8, 11, 26]); `E0s: average` gives E0(C) = E0(N) and
    E0(H) = 2·E0(O), as the doc predicted from the composition rank.
  - Times (log timestamps, job 11745195): setup 4 min 42 s (start 10:50:07, training
    10:54:49); epoch 0 224 s, epoch 1 212 s (each with its validation); post-training
    metrics on train and valid about 2 min. 200 epochs ≈ 12 h (200 × 218 s; the doc
    estimated 10 h): fits one 24 h job.
  - GPU Tesla V100-SXM2-32GB; peak 14004 of 32768 MiB (`gpu_usage.log`, one sample per minute).
- Decisions:
  - Smoke run on `sequana_gpu_dev` replaces the toy job on `sequana_cpu_dev` (agent: it
    checks compute-node mounts, `conda_sh`, the env and the ledger in one job). Owner: "Ok
    pra tudo, mete ficha" (also for: commit the pending doc edit, env record, smoke run,
    training).
  - Smoke at 20 min, the account's limit on `*_dev` (agent, under that ok). Cancelling
    11745176, a never-runnable job of the agent, was done under the same ok, without a
    separate ask.
- Problems:
  - The first session ended without `/end-session`: no journal, status or push until this
    session (cause unknown; the login node's `ulimit -t 1800` is a hypothesis, not checked).
  - 11745176 pending with `AssocMaxWallDurationPerJobLimit`: the smoke asked 30 min; the
    association `acmes` caps `*_dev` at 00:20:00 (sacctmgr). Root cause: the limit was not
    checked when the doc was written. Fixed in `7ca6665`.
  - 11745195 FAILED (`mace_run_train rc=124`, the job's own `timeout`): training ended and
    the models were saved at 11:02:34; `timeout` stopped MACE at 11:05:07 during the
    post-training plot inference (`plot=True`, MACE default; last log line
    `Running inference on train_Default dataset`). A limit of the 20 min smoke, not a
    training error.
  - Chain caveat (MACE source, `mace/tools/train.py`): with `save_all_checkpoints: False`
    a checkpoint is written only when the validation loss improves, so a job resubmitted
    with `restart_latest` resumes from the best epoch and restarts its patience count.
    Not expected to matter (about 12 h in a 24 h job).
  - Smoke log: `Skipping evaluation for heads: ['pt_head']` with
    `multiheads_finetuning: False`; the final model's heads are to be checked before MLMD.
  - Commit author on SDumont is `fileti-fileti` (git config); on neumann `Eudes Fileti`.
- Next: next SDumont session: job 11745412 (DONE or FAIL, chain jobs, ledger). Then the
  metrics script in `src/` (+ tests) before the test evaluation; `eval_configs` on
  `test.xyz` (ask first; `*_dev` max 20 min); register the result; apply the ID-1 rule.

## 2026-11-17 — neumann — Project start
- Goal: start pb-mace from lab-template (`docs/new-project.md` steps 1–5) and leave the first
  SDumont session ready. Added during the session: locate the training dataset; compute the
  AIMD reference RDFs.
- Interview summary (approved by the owner: "Aprovado!"; later answers folded in):
  - Goal: train a MACE MLFF on an existing, already labelled Prussian-blue dataset; test and
    validate it; run MLMD with it and compare its RDFs with the AIMD RDFs.
  - Out of scope now: dataset generation, CP2K runs, active learning.
  - Data: energies and forces; no stress/virial (owner: "strain" = stress/virial, not
    available for Prussian blue). Other training files are on SDumont; the owner shows their
    path at the first SDumont session. The dataset reaches SDumont from the owner's Mac.
  - Machines: training and MLMD on SDumont; neumann for setup and the AIMD RDFs.
  - Compute: training partition chosen with the owner on SDumont; cost unit unknown; ask
    before every job.
  - Confidentiality: nothing confidential, but unpublished: private repo.
  - Language: ADR-0006 defaults.
  - Validation plan (owner): short MLMD runs of interface-1, cubo222 and cubo-puro; their
    RDFs compared with AIMD RDFs of the same systems.
- Done:
  - Repos (step 2): `origin` renamed `template` (`~/git/lab-template.git`); `origin` =
    `git@github-pb-mace:fileti-fileti/pb-mace.git` (private, created by the owner on the web);
    deploy key `pb-mace@neumann` (`SHA256:DIlHM3ZK4icobonV67LUciWUtaocQZZFIowRlNUZYT8`),
    alias appended to `~/.ssh/config` by the owner; `core.hooksPath .githooks`.
  - Store (step 3): `/home/eudes/pb-mace-store/{data,runs,logs}` + symlinks, all ignored.
  - Checks (step 5): 52 tests OK; `detect` → neumann; `session_facts.py` readable.
  - `757f3cb` project start (Project section, status block, ADR-0013, ADR-0001 accepted,
    glossary); `8440102` ADR-0014 and validation plan; `git push -u origin main`
    (origin/main = `8440102`). `c0f6bfb` neumann address from the Mac (YAML comment).
  - Dataset located (owner confirmed): `~/prussian-blue/cubo/dataset/consolidado/`
    (2026-11-16 22:38). From `MANIFEST.txt`: train 2554, valid 320, test 173 frames
    (`todos.xyz` 3047); `REF_energy`/`REF_forces` in eV, eV/Å; protocol qz; split by groups
    (20 consecutive AIMD frames; event windows), stratified by config_type, seed 2026,
    val 0.10, test 0.05. The files match the MANIFEST md5s, and `consolida_dataset.py`
    matches its recorded md5. `dataset_final/` (2026-10-19, 3288 frames, keys
    `energy`/`forces`, no split) is an earlier version. sha256 (also in
    `/home/eudes/pb-mace-store/data/consolidado.sha256`):
    ```
    7842446de21f1585f5107ea1fa63e0d3f4f94077e6f8c0f0ec49656afd047a9a  frames.tsv
    51dbb49e6dd527885e2ad9ba73a68a092587c1231d4fd3b84b2d53fac5edb97d  MANIFEST.txt
    80c3704e956c797779d90ecced763dc1b15bd8281c0e2b751d8eddfbb1ba626d  test.xyz
    a3d30b35cfa6b4e3e03f1b1ea48df733b8b80ba7e8cc2f4c92a30f735cf10930  todos.xyz
    ecbe54ed332f214890dc62d4bb6dec3c381fdc7a50aa58804f2c856ef397dc18  train.xyz
    c7bd603d822d0a7a32e7a07ad71fc6396a351c5d06af0bcf1f01feb80193a139  valid.xyz
    ```
  - `e888154` experiment doc `docs/rdf-mlmd-vs-aimd.md`, `src/rdf.py`,
    `configs/rdf/aimd_reference.json`, `tests/test_rdf.py` (5 tests, skipped without numpy).
    Cross-check against MDAnalysis 2.10.0 `InterRDF` on cubo-puro Fe3–N and Na–C:
    max |Δg| 7.03e-07. `c2757f0` fix: the block check reports the maximum of g(r).
  - AIMD reference RDFs, interactive on the headnode (`analysis` env) at `c2757f0`, run dir
    `runs/aimd-rdf-reference/`: cubo-puro 1143 frames (steps 672–8666, stride 7), cubo222
    501 (steps 500–5500, stride 10), interface-1 501 (steps 500–5500, stride 10; stitched
    from 47 pieces of `interface-1np-new/longa/`). `3f65ae6` registered
    `results/aimd-rdf-reference/` (26 `.dat` + `run_info.json`; `--check` OK). The PNG
    plots stay in the run dir.
  - Ledger: `cost_ledger.py add --since 2026-11-17`: 0 rows added, 6 ended jobs outside
    the project skipped (no Slurm job this session).
- Results: AIMD reference RDFs (descriptive, no claim) in `results/aimd-rdf-reference/`.
  Block check (`run_info.json`): for several pairs (e.g. cubo222 C–N and O–H) the error at
  the maximum of g grows with the block length, so the 5-block error is a lower bound there.
- Decisions:
  - ADR-0013 lighter decision process and ADR-0001 accepted (owner: "Aprovado!");
    ADR-0014 SDumont clone in `/scratch` (owner: "ok").
  - Dataset = `consolidado/` (owner).
  - `docs/rdf-mlmd-vs-aimd.md`: pairs (owner: "Os pares escolhidos são perfeitos! Os mesmos
    devem ser escolhidos na análise das MLMD!"); generation at 400/60 and labels at 700/70
    by design (owner); stitched trajectories are fine for static properties (owner);
    reference = the `-new` AIMD runs (the May–July runs have no +U, no Na and ran at 300 K).
  - Not decided: MLMD cells. The doc says the same cell as the AIMD (agent's proposal: a
    fair comparison needs the same system); the owner raised replicating the small cells or
    testing on cubo222 only.
  - Plan B (git bundle carried through the Mac) dropped once GitHub worked.
- Problems:
  - The "bootstrap kit" cited in `docs/new-project.md` and the template status does not
    exist in the template's files: SDumont follows step 6 (clone from GitHub).
  - The harness denied the agent's write to `~/.ssh/config`; the owner appended the alias
    (the same will apply on SDumont).
  - `ssh -T github-pb-mace`: "Permission denied (publickey)" twice; `ssh -v` showed the
    right key offered and refused. Root cause: the deploy key was not saved on GitHub (the
    owner's 2FA login failed: SMS codes not arriving). Fixed by the owner.
  - No `gh` on neumann, and a deploy key cannot create repos: the owner created the repo.
  - The first RDF run labelled argmax(g) as the "first peak" (cubo222 Na–O maximum at
    8.25 Å): fixed in `c2757f0` and rerun; the registered files come from `c2757f0`.
  - `interface-1np-new/longa/`: 38 of 85 `parte_*` dirs hold no trajectory; steps 0–110
    are absent (inside the discarded 0.5 ps).
- Next: the SDumont session (status block, Now). Before any MLMD run: MLMD cells, protocol
  and agreement criterion in `docs/rdf-mlmd-vs-aimd.md`, plus the pending claim. Before
  training: the experiment doc for MACE training and test.

