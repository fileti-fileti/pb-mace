# MLMD vs AIMD radial distribution functions

## Question
Does MLMD with the pb-mace MACE model reproduce the AIMD radial distribution functions of
interface-1, cubo222 and cubo-puro?

## Design
**AIMD reference** (owner's legacy runs, read-only, ADR-0008; protocol from each run's
`LEIAME.txt` and `aimd.inp`): NVT, CSVR 100 fs, 350 K, UKS PBE-D3(BJ), U 6 eV on Fe3 only,
cutoff 400/60, H mass 2.0141. Paths under `~/prussian-blue/cubo/dataset/` on neumann.

| System | Trajectory | Atoms (kinds) | Cell (Å) | Frames written | Discarded |
|---|---|---|---|---|---|
| cubo-puro | `cubo-puro-new/cubo-puro-new-pos-1.xyz` | 60 (Fe2 4, Fe3 4, C 24, N 24, Na 4) | 10.170 cubic | 1239, every 10.5 fs | t < 1.0 ps |
| cubo222 | `cubo222-new/cubo222-new-pos-1.xyz` | 530 (Fe2 30, Fe3 32, C 180, N 180, Na 24, O 28, H 56) | 20.340 cubic | 551, every 10 fs | t < 0.5 ps |
| interface-1 | `interface-1np-new/longa/` (47 pieces, stitched) | 267 (Fe2 8, Fe3 8, C 48, N 48, Na 8, O 49, H 98) | 10.087 × 10.087 × 36.002 | steps 120–5500, every 10 fs | t < 0.5 ps |

- Levels of theory: trajectories generated at 400/60, labels at 700/70 (qz). Owner's
  design (2026-11-17): the structure is assumed essentially the same at both cutoffs,
  unlike the electronic part.
- Interface stitching: the driver restarted from earlier checkpoints, sometimes with new
  velocities. The pieces are read in run order (list in the config); a frame whose step is
  <= the last kept step drops the kept frames from that step on (the last branch through a
  step wins). Discontinuities do not matter for a static property (owner, 2026-11-17).
- Kinds: Fe2/Fe3 from each run's `COORD.inc`; the code checks that their elements match
  the trajectory, atom by atom.
- **Pairs** (owner, 2026-11-17: "Os pares escolhidos são perfeitos! Os mesmos devem ser
  escolhidos na análise das MLMD"):
  - framework, all systems: Fe2–C, Fe3–N, C–N;
  - sodium, all systems: Na–N, Na–C;
  - water, cubo222 and interface-1: Fe3–O, Na–O, O–O, O–H, N–H;
  - cubo222 only: Fe2–Fe3 (the other cells are too small for the Fe–Fe shell at ~5.1 Å).
- **RDF parameters**: orthorhombic minimum image; r_max = half the shortest cell edge,
  floored to a whole bin (cubo-puro 5.08, cubo222 10.16, interface-1 5.04 Å); dr = 0.02 Å;
  g_AB(r) normalised with the cell volume (ordered pairs, N_A(N_A − 1) when A = B);
  n_AB(r) = mean number of B within r of an A, counted directly.
- **Error**: the kept frames are split into 5 contiguous blocks; per-bin standard error of
  the block means. Correlation check: the error at the maximum of each g(r) is also
  reported for 2, 4, 8 and 10 blocks; an error that still grows with the block length means the
  blocks are not independent and the 5-block error is a lower bound.
- **MLMD** (fixed before any MLMD run): same cell and composition as the AIMD of each
  system, starting from one of its frames; NVT at 350 K; the same code (`src/rdf.py`),
  pairs, parameters and discarded time. Protocol: next section.
- Fair comparison (ADR-0013 rule 3): one analysis for AIMD and MLMD, fixed before the MLMD
  output is seen.

## MLMD protocol (fixed 2026-11-19, before any MLMD run)
Agent's proposal, owner's answer: "ok, no rascunho" (2026-11-19). The agent's reasons are
kept next to each choice.
- **Model**: the one `docs/mace-training.md` fixes before any MLMD (now `pb_mace_v2`, by
  its validation-loss rule), converted with MACE's `create_lammps_model` (mace_env). The
  claim records the sha256 of the `.model` and of the LAMMPS file.
- **Engine**: LAMMPS with the MACE pair style, the own build in
  `configs/machines/sdumont.yaml` (`pair_style mace no_domain_decomposition`, as the
  owner's legacy MLMD `pb/mlmd/prod/md_nvt.lmp`), 1 GPU, float64; elements Fe C N O H Na.
  MACE has one Fe element; Fe2/Fe3 are labels by atom index (`kinds.inc` in the run dir).
- **Start** (changed 2026-11-19, before any MLMD run; the AIMD trajectories stay on
  neumann; owner's answers under Reading rule): the first frame of the system's
  config_type in `data/consolidado/train.xyz` (cubo_puro, cubo222, interface_longa: frames
  of the same AIMD runs, training side; cell and composition checked against the AIMD);
  new Maxwell–Boltzmann velocities at 350 K for each seed, zero total momentum.
  Fe2/Fe3 from its geometry: Fe2 = Fe with a C within 2.4 Å (the C-bound site), Fe3 = the
  other Fe; the counts equal the AIMD's (4/4, 30/32, 8/8; checked 2026-11-19).
- **Dynamics**: NVT 350 K, Nosé–Hoover chain with a 100 fs time constant
  (`fix nvt temp 350 350 0.1`, as the owner's legacy MLMD), H mass 2.0141 as the AIMD.
  The AIMD's CSVR (`fix temp/csvr`) is not in this LAMMPS build (`lmp -h`, 2026-11-19:
  packages KSPACE ML-MACE MOLECULE OPENMP RIGID). Timestep: the AIMD's, 1.5 fs
  (cubo-puro) and 1.0 fs (cubo222, interface-1): time / step of the trajectory headers
  (`results/aimd-rdf-reference/run_info.json`). In classical NVT, g(r) depends on neither the
  masses nor the thermostat; time constant and masses are matched so that the time
  correlation, and with it the block statistics, stays comparable.
- **Length and seeds**: per system, 5 replicas (seeds), each with the AIMD's length,
  discarded time and frame interval (table above). Each replica repeats the AIMD design,
  so the spread of a quantity over the replicas estimates the fluctuation of one
  AIMD-length run, which the AIMD's 5-block error underestimates (Results, block check).
  MLMD time per system: 5 × the AIMD's.
- **Output**: frames at the AIMD interval, atom order unchanged, in a format `src/rdf.py`
  reads (reader or converter written and tested before the MLMD).
- **Checks before production** (tests and toy jobs: exempt from the reading rule; each
  job asked first; `*_dev`):
  1. LAMMPS vs `mace_eval_configs` on the start frame of each system: energy within
     1e-6 eV/atom and every force component within 1e-5 eV/Å (float64 in both). Target:
     cells with an edge < 2 r_max = 12 Å (cubo-puro; interface-1 in x and y) and the Na map.
  2. Speed per system (steps/s on 1 V100): sets the job length and the chain.
- **Instability**: a replica that loses atoms or gives a non-finite energy or force is a
  model failure and counts in the reading rule; a node or wall-time failure is resubmitted.

## Reading rule (fixed 2026-11-19, before any MLMD run)
Agent's proposal, owner's answer: "ok, no rascunho" (2026-11-19). Changed the same day,
before any MLMD run: σ from the replicas only (below). Owner (2026-11-19): "vamos
prosseguir sem as trajetorias da neumann. vamos fazer a mlmd e comparar apenas com as RDFS
q já temos"; the agent's proposal of the three changes (start frame, Fe2/Fe3, σ); owner:
"ok, faça tudo e estime a duracao do teste". Never changed after the MLMD output is seen
(a changed rule makes a new claim).
- **Quantities per pair and system**, from g_AB and n_AB of `src/rdf.py` (extension
  written and tested before any MLMD output). First peak: from contact to r_c, the first
  local minimum after the first local maximum of the AIMD's g_AB (both on its 5-bin
  running mean); the same window for the MLMD. Not the global maximum: in cubo222 the
  Na–O contact peak (~2.3 Å) is lower than the maximum at 8.25 Å.
  - r1: position of the highest bin of the first peak (parabola through it and its two
    neighbours);
  - n1: n_AB at r_c (coordination number of the first shell);
  - g1: height of the first peak, reported with its uncertainty, no verdict: twice the
    AIMD's 5-block error (a lower bound) already exceeds 10 % of g1 in 9 of the 26 pairs
    (`run_info.json`), so a g1 verdict could hardly ever be yes.
  - A pair whose AIMD g_AB has no local minimum after its first maximum within r_max gets
    r1 only.
- **Difference and uncertainty**: Δ = AIMD value (registered `results/aimd-rdf-reference/`)
  − mean over the 5 MLMD replicas; σ = s·sqrt(1 + 1/5), where s is the standard deviation
  over the replicas and stands for one AIMD-length run. The AIMD's own block error of r1
  and n1 is not available: the registered files hold g_err per bin, not per-block curves.
  Reported, no part of the rule: the AIMD's g_err at the g1 bin and the MLMD's 5-block
  error of each quantity.
- **Tolerances** (what counts as "the same"): r1 0.05 Å (2.5 bins); n1 5 % of the AIMD
  value.
- **Verdict per quantity** (r1, n1): yes if |Δ| + 2σ ≤ tolerance; no if
  |Δ| − 2σ > tolerance; otherwise inconclusive.
  - Per pair: no if any quantity is no; yes if all are yes; otherwise inconclusive.
  - Per group of pairs in each system: framework (Fe2–C, Fe3–N, C–N, Fe2–Fe3), water
    (O–O, O–H, Fe3–O, N–H), Na (Na–N, Na–C, Na–O; limit 7). No if any pair is no or any
    replica is unstable; yes if all pairs are yes; otherwise inconclusive.
- **Claim**: one verdict per group and system (cubo-puro: framework, Na; cubo222 and
  interface-1: framework, water, Na), no overall average; the pending claim goes to
  `docs/claims.md` with this rule once the owner approves it.
- Limits known now:
  1. The 400/60 vs 700/70 assumption above.
  2. Frames of these trajectories are in the training set: the comparison tests
     reproduction, not generalisation.
  3. Short AIMD runs (5–12 ps) with correlated frames: large error bars on the reference,
     so "inconclusive" is a possible outcome.
  4. r_max ≈ 5 Å in cubo-puro and interface-1.
  5. interface-1 is a slab: g(r) is normalised with the whole cell volume, so it does not
     tend to 1 at large r and its heights are not comparable with the bulk systems; the
     MLMD uses the same normalisation, so the comparison is unaffected.
  6. s rests on 5 replicas and assumes that MLMD and AIMD have similar correlation
     times; the AIMD's own error is no floor: if the MLMD decorrelates faster, σ is too
     small and "no" too easy. The MLMD's own 5-block errors are reported next to s as a
     check.
  7. Na reference forces (found 2026-11-19, monitoring of `pb_mace_v2` on `valid.xyz`;
     training-side data only). In every Na-containing frame the reference forces do not
     sum to zero: median |ΣF| 1.1–3.2 eV/Å per Na config_type, against 0.16–0.43 eV/Å in
     the frames without Na (`train.xyz` labels). In `valid.xyz` that net force is the sum
     of the Na residuals of the model (median cosine 0.986), and the model reproduces
     little of the reference Na forces (slope 0.18, r 0.41; other elements ≥ 0.99). Exact
     forces sum to zero and MACE's do by construction, so most of the Na "error" sits in
     the labels. Cause, from the data: a CP2K real-space grid (egg-box) error on Na. The
     Na residual is periodic in the absolute Na position with the period of the 700 Ry
     grid: a scan of the grid size N gives its best fit at exactly 162, 576 and 324
     points (the sizes for these cells) on all 9 cell axes, R² 0.54–0.74 (median 0.004–0.06
     at other N), amplitude 0.45 eV/Å; other elements ≤ 0.04 eV/Å.
     TODO(owner): why Na (its basis or pseudopotential in the qz and AIMD inputs).
     The 400/60 AIMD has it too: the Na positions of its frames (`train.xyz`) are
     non-uniform modulo the 400 Ry grid (best N 125, 450, 256). The grid ripple is the
     same in every grid cell (0.083 Å), so it should not bias the Na distribution on the
     scale of g(r) peaks (0.1–1 Å); it does affect the Na dynamics. Argument, not a test.
  8. The MLMD starts from a training frame of each AIMD run, not from the AIMD's first
     frame; the discarded time re-equilibrates it.

## How to run
- AIMD reference: `src/rdf.py configs/rdf/aimd_reference.json <run dir>` with the
  `analysis` env, interactive on the neumann headnode (light analysis, no Slurm job),
  run dir under `runs/`, clean tree; the commit is written to `run_info.json`.
- MLMD, on SDumont (2026-11-19), mace_env, from the repo root:
  1. Model: `mace_create_lammps_model runs/pb_mace_v2/MACE_models/pb_mace_v2.model
     --dtype float64 --head Default` (done 2026-11-19, login node, 12 s).
  2. Checks (test job, ask first): `scripts/prep_mlmd.py configs/mlmd/pb_mace_v2_rdf.json
     --check --name mlmd-v2-check --partition sequana_gpu_dev --exclude sdumont8042`;
     every row of `check.tsv` PASS; timesteps/s sets the production wall time.
  3. Production (ask first), per system: `scripts/prep_mlmd.py
     configs/mlmd/pb_mace_v2_rdf.json --system <system> --name mlmd-v2-<system>
     --partition sequana_gpu --time <from step 2> --exclude sdumont8042`.
  4. MLMD RDFs: `src/rdf.py configs/rdf/mlmd_pb_mace_v2.json runs/mlmd-v2-rdf`.
  5. Verdicts: `src/rdf_compare.py results/aimd-rdf-reference runs/mlmd-v2-rdf
     runs/mlmd-v2-compare --replicas 5 [--unstable <system>_r<k>,...]`; then register and
     apply the rule to claim ID-3.

## Results
- AIMD reference: `results/aimd-rdf-reference/` (`.dat` per pair and `run_info.json`,
  with the commit). Plots `rdf_<system>.png` stay in the run dir
  (`runs/aimd-rdf-reference/`, neumann) and on the owner's Mac: binary files are not
  registered; they are redrawn from the `.dat` files.
- Block check (`run_info.json`, `gmax_err_by_nblocks`): for several pairs the error grows
  with the block length, so the 5-block error is a lower bound there (owner's concern,
  2026-11-17: few frames, highly correlated).
