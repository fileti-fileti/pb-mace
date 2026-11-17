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
  the block means. Correlation check: the error at each pair's first peak is also reported
  for 2, 4, 8 and 10 blocks; an error that still grows with the block length means the
  blocks are not independent and the 5-block error is a lower bound.
- **MLMD** (fixed before any MLMD run): same cell, composition and starting structure as
  the AIMD of each system; NVT at 350 K; the same code (`src/rdf.py`), pairs, parameters
  and discarded time. TODO(owner): length, thermostat, timestep, number of seeds.
- Fair comparison (ADR-0013 rule 3): one analysis for AIMD and MLMD, fixed before the MLMD
  output is seen.

## Reading rule (fixed before the MLMD output is analysed)
- TODO(owner): agreement criterion per pair (yes / no / inconclusive), fixed before any
  MLMD output is analysed; the pending claim goes to `docs/claims.md` with it.
- Limits known now:
  1. The 400/60 vs 700/70 assumption above.
  2. Frames of these trajectories are in the training set: the comparison tests
     reproduction, not generalisation.
  3. Short AIMD runs (5–12 ps) with correlated frames: large error bars on the reference,
     so "inconclusive" is a possible outcome.
  4. r_max ≈ 5 Å in cubo-puro and interface-1.

## How to run
- AIMD reference: `src/rdf.py configs/rdf/aimd_reference.json <run dir>` with the
  `analysis` env, interactive on the neumann headnode (light analysis, no Slurm job),
  run dir under `runs/`, clean tree; the commit is written to `run_info.json`.

## Results
- AIMD reference: `results/aimd-rdf-reference/` (when registered).
