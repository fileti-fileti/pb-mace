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

