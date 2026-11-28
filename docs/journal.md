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
## 2026-11-27 — neumann — q1 check: seed done, rule v2, the four settings running
- Goal: finish the q1 seed and run the q1 check of the Na relabelling (ADR-0016).
- Done:
  - `/start-session`: in sync with `origin`; the ledger row of 4405 (added 2026-11-25) was
    uncommitted: `aea65a4`, pushed (owner "faça o push").
  - Seed resubmitted from scratch with `sbatch --time=06:00:00 job.sh` (owner "resubmete a
    semente"): job 4415 COMPLETED in 28:49 (46.1 core-h); ledger `ee7afa2`.
  - Diagnostic `runs/na-q1-check/q9-seed-diag` (owner "monta o diagnostico", "submete!"):
    hand-made at `ee7afa2` from the q1 seed dir, Na KIND of the q9 settings; its input
    equals the legacy `rotulagem/b01/relabel.inp` except the geometry; reading fixed in its
    `run_info.json`. Job 4416 COMPLETED in 1:16:45 (122.8 core-h).
  - `10f3511`: q1 check Result v1 and rule v2 in `docs/na-relabel.md`, the relabel's state
    criterion amended to match, `src/na_q1_check.py` state test v2 + 3 tests, ledger 4416
    (owner "ok vamos de v2", "aplica"). Suite: 168 tests OK.
  - Jobs 4417 (q9-c700), 4418 (q9-c2000), 4419 (q1-c700), 4420 (q1-c2000) submitted at
    18:40 on n12, clean tree at `10f3511` (owner "submete"). 4417 COMPLETED in 11:00
    (17.6 core-h); ledger +1 row at session end.
- Results:
  - q1 check v1: inconclusive, the seed check failed (`docs/na-relabel.md`, Result v1).
    - q1 seed: max |Δspin| 0.0223 > 0.01 against the f01 legacy label; total spin 40.000.
    - The 8 high-spin Fe(III) are within 0.002. The deviations are on low-spin Fe(II):
      Fe 61 +0.022, Fe 62 −0.021, Fe 63 +0.011.
  - Diagnostic 4416: SCF not converged (10 × 100 steps); non-physical Mulliken (net charge
    10.3, total spin 58.7). The origin of the 0.022 is not known.
  - Seed speed: 4415 ran ~7 s per SCF step alone on n12, 4405 ~50 s while it shared n12
    with job 4403 (outside the project). Contention suspected, not verified.
  - Interim, read at 22:25 (not a verdict; rule v2 is applied when all four end):
    - q9-c700 reproduction check passes: max |ΔF| f01 0.02, f10 0.00 meV/Å (≤ 10).
    - q9-c2000: the 7 ended frames converged.
    - q1-c700: 6 of 8 ended frames converged. f03 and f06 did not (Mulliken total spin
      21.9 and 49.8).
    - q1-c2000: f01 and f02 converged; f03 still unconverged after 900 steps.
  - The "DFT+U energy contribution is negative" warning is printed at every SCF step of
    every point, converged ones included: it is not a collapse marker.
- Decisions:
  - Owner: "resubmete a semente"; "monta o diagnostico" (after the agent advised the
    diagnostic first: ~46 core-h against the check's ~1.5–4.3k); "ok vamos de v2"
    (state test by Fe spin class and total spin, fixed before any setting ran); "aplica";
    "submete".
  - Agent, in the diff the owner applied: the relabel's Protocol state criterion follows
    rule v2.
- Problems:
  - 4405: TIMEOUT at 2:00:24. Root cause: the agent's 2 h `seed_job_time` in
    `configs/na_relabel/q1_check.json`. The legacy protocol needs 230–281 SCF steps per
    snapshot (`rotulagem/b01`).
  - 4416: "SCF run NOT converged" after the U ramp started. Na q9 with the atomic-guess
    protocol is not robust on f01, while q1 converged on the same frame (238 steps).
  - The first diagnostic input was wrong: the agent's `sed` also changed the H potential
    (GTH-PBE-q1 → q9). The diff caught it before submission; the input was rebuilt by
    replacing only the `&KIND Na` block.
  - q1-c700 f03 and f06: "SCF run NOT converged". Every q1 frame restarts from the q1 seed
    (f01's state) with the full U; the q9 frames restart from `chute.wfn`. Root cause not
    known.
- Next:
  - neumann, when 4418–4420 end: `cost_ledger.py add`; `python3 src/na_q1_check.py
    runs/na-q1-check` (rule v2); register (ask which files, with `q9-seed-diag`); apply the
    verdict to ADR-0016.
  - If the q1 SCF failures leave fewer than 9 valid frames, the verdict is inconclusive by
    the rule. q1 SCF robustness is then a new question for the relabel (owner).

## 2026-11-25 — neumann — Na grid error confirmed (v2); focus on the PB(100) slab; q1 check started
- Goal: read translation test v2 and choose the Na label fix. After the owner moved the focus
  from the nanocube to a PB(100)/water slab: prepare the slab test and the Na relabelling.
- Done:
  - `/start-session`: fast-forward pull of the SDumont session of 2026-11-21 (`7fc9fb5`,
    `98f5a76`).
  - `a6cadb7` `src/na_label_stats.py` + 8 tests: net force of the Na labels per
    config_type, TS vs equilibrium frames, rule fixed before the run (owner "faz a
    checagem"). Run `runs/na-label-stats` at `a6cadb7`, clean tree. Not registered (owner:
    "Nao vamos por esse caminho").
  - Web literature search on Prussian-blue/PBA–water interfaces (agent; not a formal
    bibliographic check; summary in ADR-0015, Context).
  - Jobs 4392–4397 COMPLETED; ledger +6 rows (599 core-h); `src/na_translation.py
    runs/na-translation-test-v2`; registered `results/na-translation-test-v2/`
    (`analysis/*`, `run_info.json`), `e63ab21`.
  - `f9afc7a` `scripts/prep_mlmd.py`: optional `replicate` key; 2 new tests (fail on the old
    script, pass on the new). `configs/mlmd/slab100_test.json`: 3×3 slab. Build check on
    the real frame (train.xyz frame 1352, `interface_longa:1`): 2403 atoms,
    30.261 × 30.261 × 36.002 Å, Fe2/Fe3 72/72 recomputed = copies, closest atoms of
    different copies 0.94 Å.
  - `5bcc028` ADR-0015, ADR-0016, `docs/na-relabel.md` (q1 check rule), v2 result in
    `docs/na-label-grid-error.md`, `CLAUDE.md` Project.
  - `57c4487` `scripts/prep_na_q1_check.py`, `src/na_q1_check.py`,
    `configs/na_relabel/q1_check.json`, 13 tests. `46ca661` eligibility fix (Problems).
    Suite: 165 tests OK.
  - Prep at `46ca661`: `runs/na-q1-check`. Against the legacy inputs only the planned lines
    differ (seed file, one snapshot, cutoff, Na KIND); the geometry and reference forces in
    all 38 frame dirs equal the legacy files; `seed_q9.wfn` sha256 = `chute.wfn`.
  - Job 4405 (q1 seed, n12, 96 MPI × 1) submitted at 16:45; running at session end.
- Results:
  - Translation test v2, by its rule (`docs/na-label-grid-error.md`, Result v2): check
    0.53 meV/Å; diagnosis confirmed (s_Na 289.7 meV/Å, 28.9× the largest host spread);
    q1-c700 fixed (s_Na 0.0), q9-c1600 not fixed (33.4), q9-c2000 fixed (7.2), q9-c2400
    fixed (2.4). Reported only: q1-c700 vs q9-c2400 RMS ΔF Na 59.2, N 22.7, Fe 16.7,
    C 11.4 meV/Å; wall time vs q9-c700: 2.1× (1600), 3.8× (2000), 3.6× (2400), 1.2× (q1).
  - Na label net force, by its rule (monitoring, `runs/na-label-stats/verdict.json`):
    "same". x = |ΣF|/√n_Na: TS n 224, p90 1.011, max 1.541 eV/Å; equilibrium n 134, p90
    0.929, max 1.330; r_p90 1.088, r_max 1.159. The TS labels are not worse than the
    equilibrium ones.
  - The interface-1 cell is already a PB(100) slab with water on both faces; interface-2
    (legacy AIMD, 687 atoms, no Na, AFM) is all Fe(III) by formal count (ADR-0015).
  - Agent's cost estimates: relabelling the 1350 Na frames with q1 ~33–46k core-h; q1 check
    ~1.5–4.3k core-h (`docs/na-relabel.md`).
- Decisions (owner):
  - "acho q poderiamos mudar um pouco o foco ... simular uma interface infinida em 2D, uma
    slab" and "vamos. preparar a slab, e fazer alguns testes iniciais. em paralelo vamos
    focar na nova rotulacao", then "ok" to the five proposals: ADR-0015 (slab is the main
    object, nanocube dropped, Na relabelling in scope, interface-2 later); ADR-0016 (Na q1
    at 700/70, on the q1 check); the q1 check; relabelling in two phases; the 3×3 slab test.
  - "ok pra tudo": diffs applied and committed, v2 registered, the q1-c2000 control kept.
  - "submeta o job": 4405.
  - Agent: the q1 check eligibility was amended before any input was written (doc); the
    reading rule is unchanged.
- Problems:
  - First q1 check prep stopped: "eventos/interface-1np/N3/rotulos/j01/relabel.out snapshot
    11: input differs beyond ['LAST_SNAPSHOT', 'SEED', 'STEPS']". Root cause: 3 legacy label
    jobs (N3 j01, one W4a, one longa) used another state protocol (atomic guess or
    USE_PREV_WF); the draw now takes only seeded origins (`46ca661`).
- Next:
  - neumann, when 4405 ends: `cost_ledger.py add`; seed check (SCF converged, Fe spins
    within 0.01 of f01's legacy label); then ask to submit the four settings in
    `runs/na-q1-check`.
  - After those end: `python3 src/na_q1_check.py runs/na-q1-check`, register, apply the rule
    to ADR-0016.
  - SDumont: ID-3 jobs; slab test `prep_mlmd.py configs/mlmd/slab100_test.json --check`
    (ask), then the NVT.

## 2026-11-21 — sdumont — ID-3 MLMD fixed and resubmitted; nanocube proposed
- Goal: read the MLMD production jobs 11753217–19 and get the ID-3 MLMD running; assess the
  owner's nanocube (`nanocubo_vac.pdb`, neumann) as the main MLMD object.
- Done:
  - `/start-session`: in sync with origin at `d59e0d2`, tree clean, no pull. Jobs
    11753217/18/19 FAILED 1:0 on 2026-11-20 13:31 after 36–37 s; 0 of 5 replicas DONE each.
  - `7fc9fb5` `scripts/prep_mlmd.py` IN_PROD: `dump_modify ... format line "%s %.6f %.6f
    %.6f"`; `tests/test_prep_mlmd.py` asserts the full line and no `format float` (fails on
    the old line, checked with `git stash`). Suite: 142 tests OK (`python3` 3.10.20 and
    `mace_env`).
  - Re-prep at `7fc9fb5` with the 2026-11-20 arguments (sequana_gpu, exclude sdumont8042, 6
    CPUs, 1:30/3:15/2:15): `runs/mlmd-v2-{cubo-puro,cubo222,interface-1}-r2`. Against the
    failed dirs only the commit, job name, `RUN=` and the dump_modify line differ
    (`start.data`, `kinds.inc`, model and config sha256 identical). Failed dirs kept.
  - Input check on the login node (it has 2 V100 GPUs; the CUDA path ran) in
    `runs/mlmd-v2-r2-skiprun/` (commit recorded): `lmp -skiprun` parsed the three inputs
    with no ERROR but skips `run` entirely in LAMMPS 10 Sep 2025; a test copy with `run 20`
    (`in_short.lmp`): rc=0, no ERROR/WARNING, 3 frames each, every atom line with 6
    decimals; `src/rdf.py` `iter_xyz` reads them (60/530/267 atoms, step × dt right).
  - Jobs 11754110 `mlmd-v2-cubo-puro-r2`, 11754111 `mlmd-v2-cubo222-r2`, 11754112
    `mlmd-v2-interface-1-r2` on sequana_gpu, RUNNING since 2026-11-21 06:20; after ~5 min
    rep1 at step 7560/8666, 1500/5500, 2370/5500, no ERROR.
  - Nanocube coverage in `data/consolidado/train.xyz` (scratchpad scripts, not kept):
    Results. SDumont has GROMACS modules (2023.2, 2024.1, 2026.0 builds, among others); no
    Packmol module, none in `mace_env`. `data/nanocubo/` created, empty, for the owner's copy.
  - Ledger: 3 rows added (11753217–19, FAILED, 36/37/36 s); 0 jobs outside the project
    skipped. Glossary: Committee, Fe motif, Nanocube, Receptive field.
- Results (monitoring, not claims):
  - 11753217–19, all 15 replicas: `ERROR: Unknown dump_modify format keyword: float
    (src/dump.cpp:1219)`; dump xyz takes only `format line` or `format none`.
    `mlmd-v2-check` runs IN_CHECK (dump custom, where `format float` is valid), so IN_PROD
    had never been parsed by LAMMPS.
  - Training Fe motifs (nC, nN, nO within 2.6 Å): (0,3,3), the 24 nanocube edge Fe(III):
    0 (at most 2 O on an Fe(III), `vacancia_*`); Fe(II) with 2 terminal CN (12 edge sites of
    a 5×5×5 lattice without corners): 15 of 13 755; covered: (0,5,1) 4429, (0,6,0) 7272,
    Fe(II) with 1 terminal CN 3215 (`interface_*`). So ~36 of the 116 nanocube Fe sit in
    environments absent from training; ID-3 (periodic systems) does not test them.
  - Every `interface_*` config_type has Na; the Na-free framework config_types are
    `vacancia_*` only. Na nearest-N distance per config_type: median 2.51–2.66 Å; the
    owner reports 2.59 Å for all nanocube Na.
  - `pb_mace_v2` receptive field: r_max 6 Å × 2 layers = 12 Å (LAMMPS log).
  - Nanocube from the owner's description (file not read yet): 62×3 + 54×2 − 324 = −30,
    closed by 30 Na⁺; 1124 atoms. Agent's estimates, not measured: 0.8/1.0/1.2 nm of water
    → box ~42/46/50 Å, ~6.8k/9k/12k atoms; cube rotation ~10–15° in 100 ps
    (Stokes–Einstein–Debye, radius ~13 Å, real-water viscosity), enough at 0.8 nm to bring
    the cube–image gap below 12 Å.
- Decisions (owner):
  - "commit. aplica o diff": `7fc9fb5`. "ok rode o ID-3": the three resubmissions. The
    doc's failure rule covers model and node/wall-time failures only; this was an input
    error with 0 MD steps and no output read, so the ID-3 rule is unchanged (agent).
  - "O modelo deve ser o v2": ID-3 and the nanocube MLMD with `pb_mace_v2`.
  - "ADR ok": ADR-0015 for the nanocube, from the agent's proposal: keep the 30 Na
    (without them the system is −30 or has 30 Fe(II)→Fe(III), and its surfaces are Na-free,
    unlike every training interface); 1.0 nm of water (20 Å between images) with a
    density-profile check after the NPT; remove the cube's rotation in LAMMPS (`fix
    momentum N angular rescale` on the cube; COLVARS orientation if available); water
    density from a classical GROMACS NPT with the cube restrained (no stress in the model);
    the edges need a committee or a declared limit (open).
  - Nanocube work on SDumont (owner's proposal; the agent agreed: model, LAMMPS and MLMD
    are here; the original stays on neumann).
  - Input test on the login node in `/scratch`, not in a queue (owner asked why not a normal
    queue; agent: a queued test waits as long as the production, and a bad input fails the
    production in ~40 s anyway); owner: "segue o teste".
- Problems:
  - 11753217–19 FAILED, root cause above. Not caught by `mlmd-v2-check` nor by the unit
    test (it asserted only the start of the dump_modify line). The two 2026-11-20 neumann
    sessions carried "production submitted" after the jobs had failed at 13:31.
  - `lmp -skiprun` does not run setup or write a dump in this LAMMPS; a short-run copy was
    needed.
  - The nanocube and the October solvation inputs (Packmol, GROMACS topology, `.mdp`) are
    on neumann only; Na count not checked. neumann login: YAML `eudes@172.20.22.62`, the
    owner's prompt `fileti@neumann`.
  - The agent first gave the training Na–N median as 2.60–2.66 Å; the output gives
    2.51 (`interface_aimd`) to 2.66.
- Next:
  - SDumont: 11754110–12 (DONE/UNSTABLE/FAIL per replica), then the MLMD RDFs, `src/rdf_compare.py`,
    register, ID-3 rule.
  - Nanocube: the owner copies neumann → Mac → `data/nanocubo/` (tar over ssh; manifest
    `nanocubo.sha256` made on the Mac with `shasum -a 256`); then `sha256sum -c`, element
    counts (expected Fe 116, C 324, N 324, Na 30, O 110, H 220), and the ADR-0015 draft
    after the owner's answers (committee; `gmx solvate` + envelope filter vs a Packmol env;
    path of the October files; the nanocube MLMD's question and temperature).
  - neumann: translation test v2 (jobs 4392–4397) as in its Now.

## 2026-11-20 — neumann — Translation test v1 inconclusive; v2 (state held) submitted
- Goal: read the translation test v1 (jobs 4385–4391) and run the v2 (owner: "aprovo v2.
  Submeta").
- Done:
  - `/start-session`: in sync with origin at `50818f4`; tree dirty (4 untracked files), so
    no pull. Jobs 4385–4391 all COMPLETED 0:0 on n12 (ended 14:21–14:56).
  - Found unlogged activity after `50818f4` (14:08): `src/na_translation.py
    runs/na-translation-test` run at 15:04 (`analysis/`); `cost_ledger.py add` at 15:05
    (rows 4385–4391); v2 prep, test and config written 15:16–15:17. Read, then committed:
    `6eaf0a6` (ledger), `d1af820` (`scripts/prep_na_translation_v2.py`,
    `configs/na_translation/translation_test_v2.json`, `tests/test_prep_na_translation_v2.py`).
  - Checks before submission: seeds in the label's state (max |Fe spin − label|: the
    cubo_puro-q9-c1600 v1 output 0.001 at shift 0, 0.000 at the last shift; vacancia-q9-c700
    0.000 and 0.001); prep at `d1af820` passed all checks (`runs/na-translation-test-v2/`);
    inputs differ from the legacy ones only by PRINT_LEVEL, CUTOFF, `SCF_GUESS RESTART` +
    `WFN_RESTART_FILE_NAME seed.wfn`, no `INIT_U_RAMPING_EACH_SCF`, `U_RAMPING 0.0` and one
    snapshot; `cp2k.psmp --check` rc=0 on the 7 inputs (6 `shift_0` + q1 `seed_gen`).
  - Jobs on n12 (`EPYC_9734`), 28 MPI x 2 OpenMP, submitted 2026-11-20 16:02:
    4392 cubo_puro-q9-c2400, 4393 cubo_puro-q9-c2000, 4394 cubo_puro-q9-c1600,
    4395 vacancia-q9-c700, 4396 cubo_puro-q9-c700 (RUNNING at the session end);
    4397 cubo_puro-q1-c700 (PENDING, Resources).
  - `264c1c6` v2 section and reading in `docs/na-label-grid-error.md`, after submission,
    before any v2 output was read.
  - `1ff35f8` `src/na_translation.py` reads the v2 per-shift layout (dispatch on the
    run_info layout) + `tests/test_na_translation_v2.py` (6 tests); `reading()` no longer
    divides by a zero host spread. Rerun on the v1 data: `verdict.json` and `summary.tsv`
    identical. Suite: 142 tests OK (conda python), 142 OK, 18 skipped (`/usr/bin/python3`
    3.6.8).
  - Registered `results/na-translation-test-v1/` (`analysis/*`, `run_info.json`; 4 files,
    `--check` OK).
  - Ledger: `cost_ledger.py add`: 0 rows added (4385–4391 already in); 1 ended job outside
    the project skipped.
- Results:
  - v1, by its fixed rule (`results/na-translation-test-v1/analysis/verdict.json`):
    inconclusive. Shift 0 of cubo_puro-q9-c700 vs the legacy label: max |ΔF| 266.5 meV/Å
    (limit 10); diagnosis and remedies not read.
  - v1 cubo_puro-q9-c700 shift 0 sits 0.099 (max |Fe spin − label|) from the label's state;
    the shifts of q9-c700 and q9-c1200 changed state inside the 0.3 gate (ΔE −270 and
    −367 meV; dspin 0.099 and 0.135).
- Decisions (owner):
  - "aprovo v2. Submeta": the v2 and its 6 jobs. Agent's assessment given before: v2 holds
    the state but does not by itself explain the v1 shift-0 miss; it proposed a
    reading-only comparison first; the owner chose to submit.
  - "ok": the v2 reading (`264c1c6`): v1 thresholds unchanged; valid shift = Fe spins
    within 0.01 of the reference state (v1's 0.3 let changes of 0.07–0.13 through);
    ≥ 6 of 8 valid; reference = legacy label (q9) or `seed_gen` (q1); q1 vs q9-c2400
    reported only.
  - Owner's choices at the end: register v1 `analysis/*` + `run_info.json`; apply the v2
    analysis support.
- Problems:
  - Unlogged activity 15:04–15:17 after the end-of-session commit `50818f4` (analysis,
    ledger, v2 prep): no commit and no journal until this session.
  - v1's validity gate (Fe spin within 0.3 of shift 0) did not catch electronic-state
    changes of 0.07–0.13 with ΔE −270/−367 meV; those shifts counted as valid.
  - v2 reading fixed after submission (owner asked to submit first); no v2 output was read
    before it.
  - `reading()` of `src/na_translation.py` raised ZeroDivisionError on a zero host spread
    (found by the new synthetic tests; the v1 data were unaffected).
  - The harness denied a command containing `rm -rf` (project deny rule); redone without it.
  - v2 c2000 and c2400 use N from `grid_points()` (288, 300), not from CP2K outputs; if
    CP2K picks another N, the 8 shifts do not span exactly 7/8 of a grid period (the
    analysis reports the real phases).
- Next: when 4392–4397 end: `cost_ledger.py add`, `python3 src/na_translation.py
  runs/na-translation-test-v2`, apply the v2 reading, register (ask which files). If shift 0
  of v2 q9-c700 still misses the label: compare it with the label (spins, energy, atoms with
  the largest ΔF) before the scope decision (relabel; q9 at a higher cutoff vs Na q1).
  SDumont: as before (MLMD production 11753217–19, then the MLMD RDFs).

## 2026-11-20 — neumann — Na label cause read from the inputs; translation test submitted
- Goal: find why the Na labels make the model fail (owner: "Precisamos determinar pq a
  rotulagem do Na levou a resultados tao ruins no modelo ML"): step 1 (reading) and the
  translation test of `docs/na-label-grid-error.md`.
- Done:
  - `/start-session`: clone 18 commits behind origin, clean; `git pull --ff-only` 1264b44 →
    `c31ba17`.
  - Read, no runs: the qz inputs of all `consolidado/` sources, the AIMD input, the label
    filter, the basis/potential files and the owner's legacy cutoff test (Results).
  - `fe35fc2` `scripts/prep_na_translation.py`, `configs/na_translation/translation_test.json`
    and tests; `2b2f93f` reading rule of the translation test in
    `docs/na-label-grid-error.md`, before submission; `ba4214c` `src/na_translation.py`
    (analysis that applies that rule) and tests. Suite: 126 tests OK (18 skipped).
  - Run dir `runs/na-translation-test/` prepared at `fe35fc2` (all prep checks passed);
    `cp2k.psmp --check` SUCCESS on the 7 inputs (negative control: an invalid enum and an
    unknown keyword give rc=1). Inputs differ from the legacy ones only in the setting,
    `PRINT_LEVEL MEDIUM`, `EXTRAPOLATION USE_PREV_WF` and the REFTRAJ on 4 shifts.
  - Jobs on n12 (`EPYC_9734`), 28 MPI x 2 OpenMP each, submitted 2026-11-20 14:02:
    4385 vacancia-q9-c700, 4386 cubo_puro-q9-c1600, 4387 cubo_puro-q9-c700,
    4388 vacancia-q9-c400, 4389 cubo_puro-q9-c1200 (RUNNING at the session end);
    4390 cubo_puro-q9-c400, 4391 cubo_puro-q1-c700 (PENDING, Resources).
  - Ledger: `cost_ledger.py add --since 2026-11-17`: 0 rows added (no project job ended);
    10 ended jobs outside the project skipped.
- Results (reading of the inputs; inference, the translation test is the direct check):
  - The 391 source dirs of `consolidado/` share CUTOFF 700, REL_CUTOFF 70, default NGRIDS,
    no `&XC_GRID` and DZVP-MOLOPT-SR bases, with and without Na (legacy water:
    `agua-pura/REFTRAJ.inp`, also 700/70). CP2K 2024.1 (cubo-puro b01 header).
  - Na is `GTH-PBE-q9` (2s2p semicore) with `DZVP-MOLOPT-SR-GTH-q9`: nonlocal projector
    radii 0.144/0.130 bohr (other elements ≥ 0.21) and the largest basis exponent of the
    system, 23.52 bohr⁻² (O 10.39, H 10.07, Fe 8.42, N 7.34, C 5.61). Proxy for how well the
    700 Ry grid resolves the tightest product Gaussian, exp(−E/(8α)): Na 2.4e-2, O 2.2e-4,
    H 1.7e-4, Fe 3.1e-5; Na needs ~1600 Ry for the resolution O has at 700 Ry. Every Na q9
    basis in the CP2K 2024.1 data dir has α_max 23.5–23.8; the UZH Na q1 basis has 0.56.
  - AIMD (`cubo-puro-new/aimd.inp`): same Na q9, CUTOFF 400 / REL_CUTOFF 60 (proxy 1.2e-1).
  - Label filter (`filtra_relabel.py`): SCF converged and Fe spin gate; unconverged SCF is
    not the cause.
  - The 700/70 choice came from the owner's cutoff test (`conv_test/conv/`, stages A and
    C) on `interface-1@207/357`, the old interface without Na (48 C, 16 Fe, 100 H, 48 N,
    50 O). It was never rechecked after Na entered the `-new` systems.
  - An energy ripple of 4.5 meV per Na gives the fitted 0.45 eV/Å at h = 0.0628 Å
    (F = 2πΔE/h): energies fit (2 meV/atom), Na forces do not.
  - qz wall time per frame (one batch each): cubo-puro 233 s (56 MPI, n12), cubo222 2224 s
    (56), interface-1 longa 509 s (96), vacancia-14wat c01 1251 s (128, n09).
  - `BASIS_MOLOPT`, `POTENTIAL`, `dftd3.dat`: same sha256 in `cubo-puro-new/`,
    `vacancia-14wat/` and the CP2K 2024.1 data dir.
  - CP2K finest grids (test outputs): 162, 216, 256 points at 700, 1200, 1600 Ry
    (10.170 Å); 160 and 120 at 700 and 400 Ry (9.910 Å). Shift 0 positions: frames
    `cubo-puro-new/rotulagem/b01` #1 and `vacancia-14wat/relabel_qz/c01` #1, both train.
- Decisions (owner):
  - "Sim, segue": step 1 of the Na doc, reading only.
  - "mote o teste ... Vamos ver o resultado do teste antes": the relabel/scope decision
    waits for the test.
  - "ok": the reading rule (`2b2f93f`) and the 7 jobs. Agent's choices in the setup:
    training-side frames only; `USE_PREV_WF` for shifts k > 0 (same electronic state;
    shift 0 starts as the labels did); 28 x 2 layout from the owner's `pb_conv.py`; no
    vacancia run at 1600 Ry (the non-Na cutoff error is already in `conv_test/`).
- Problems:
  - `grid_points()` of the prep expected 250 points at 1600 Ry; CP2K chose 256, so the
    1600 Ry shifts span 0.77 of a grid period instead of 0.75. The analysis reads N from
    the output. The same CP2K choice explains the 256 quoted for 400 Ry in the Na doc.
  - The harness denied a command containing `rm -rf` (project deny rule); redone in a new
    scratchpad dir.
  - n12 is the only node free for CP2K (n09–n11 run the owner's `aimd_xgnt`); 8 jobs of
    another user (112 CPUs each) are held on `EPYC_9734` and would compete if released.
- Next: when 4385–4391 end: `cost_ledger.py add`, `python3 src/na_translation.py
  runs/na-translation-test`, apply the reading, register (ask which files), then the
  owner's scope decision (relabel; q9 at a higher cutoff vs Na q1). SDumont: as before
  (MLMD production 11753217–19, then the MLMD RDFs).

## 2026-11-20 — sdumont — MLMD production submitted; Na label context for neumann
- Goal: start the MLMD production for claim ID-3; write up the Na label (grid) error so
  that it can be worked on neumann.
- Done:
  - `/start-session`: in sync with origin at `8a21143`. Found the three production run
    dirs `runs/mlmd-v2-{cubo-puro,cubo222,interface-1}` prepared 2026-11-20 06:32 at
    `8a21143` (`prep_mlmd.py`, mode production), not submitted and not logged. Checked
    against claim ID-3 and `docs/rdf-mlmd-vs-aimd.md`: model and config sha256, nsteps × dt
    = AIMD length (13.0/5.5/5.5 ps), frame interval (10.5/10/10 fs), wall time ≈ 2× the
    estimate.
  - `4981216` `docs/na-label-grid-error.md` (evidence, affected frames and sources on
    neumann, unknowns, proposed plan) and the status-block line pointing to it; pushed.
  - Jobs 11753217 `mlmd-v2-cubo-puro` (1:30), 11753218 `mlmd-v2-cubo222` (3:15), 11753219
    `mlmd-v2-interface-1` (2:15) submitted on `sequana_gpu` from their run dirs; PENDING
    (Priority) at the session end. The run dirs record `8a21143`; `8a21143..4981216`
    changes docs only.
  - Ledger: 0 rows added; 0 jobs outside the project skipped.
- Results (monitoring, training-side data only; `docs/na-label-grid-error.md`):
  - `pb_mace_v2` on `valid.xyz`, force RMSE in frames without / with Na: H 16.3/22.5,
    C 26.8/44.3, N 29.3/81.1, O 35.0/48.4, Fe 40.2/99.0 meV/Å; Na 390.1. The other elements
    err 1.4–2.8× more in Na frames; cause unknown.
  - Reference labels (train + valid): median |ΣF| 1.05–3.15 eV/Å in the 11 Na config_types,
    0.16–0.45 eV/Å without Na; median |F| component of Na 0.24–0.30 eV/Å, below the fitted
    ripple amplitude (0.45 eV/Å).
  - 1350 of 3047 frames carry Na (train 1141, valid 150, test 59).
  - Grid spacing L/N: 0.062–0.063 Å at 700 Ry, 0.080–0.081 Å at 400 Ry. Limit 7 of the RDF
    doc quotes 0.083 Å for the ripple period: matches neither; to recheck.
- Decisions (owner):
  - "ok, commit e push": the Na doc and its status-block line.
  - "sim submete!": the three production jobs, from the run dirs prepared at `8a21143`.
  - Agent's assessment, given to the owner, not yet a decision: a relabel is a scope change
    (labelling out of scope since 2026-11-17) and needs an ADR; a translation test on one
    frame comes first; a global CP2K change may force relabelling all 3047 frames; the
    MLMD production goes ahead (framework and water groups do not rest on the Na labels).
- Problems:
  - Unlogged activity on 2026-11-20 06:31–06:32 (no commit, no journal): test metrics and
    parity written (`runs/pb_mace_v2-test/{errors,parity}/`, `runs/pb_mace_v1-test/parity/`)
    and the three production dirs prepared. The test outputs were not read this session.
  - The owner thought the production had run; sacct (since 2026-10-01) and the empty
    replica dirs showed it had never been submitted.
  - The 2026-11-19 grid-fit scripts (session scratchpad) are lost; the fit of limit 7
    cannot be rerun. The tables of this session also came from scratchpad scripts.
- Next: SDumont: watch 11753217–19 (DONE/UNSTABLE/FAIL per replica; resubmit node or
  wall-time failures only), then MLMD RDFs, `src/rdf_compare.py`, register, claim ID-3.
  neumann: the owner's scope decision on relabelling, then the reading and the translation
  test of `docs/na-label-grid-error.md`.

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

