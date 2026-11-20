# Na force labels: CP2K grid (egg-box) error

Context for the neumann session that looks for a fix (owner, 2026-11-20: "levar esse
contexto para a Neumann e lá trabalhar algum meio para contornar esse problema, talvez
fazer novamente a rotulagem desses sistemas"). Written on SDumont, 2026-11-20. All numbers
below are monitoring on training-side data (train/valid), not claims; no test output was
used.

## Summary
- The qz reference forces on Na carry an error that is larger than the Na forces
  themselves. `pb_mace_v2` on `valid.xyz`: Na force RMSE 390 meV/Å, against 19–89 meV/Å
  for the other elements; slope of prediction on reference 0.18 for Na, ≥ 0.99 for the rest.
- The evidence points to the CP2K real-space grid (egg-box): the Na labels break
  translation invariance (net force ≠ 0 in every Na frame), and the Na residual is
  periodic in the absolute Na position with the period of the 700 Ry grid.
- Affected: every frame with Na, 1350 of 3047 (11 config_types: `cubo_puro`, `cubo222`
  and all `interface_*`). The 400/60 AIMD runs that produced these frames have the same
  kind of error.
- Not known: why Na (basis or pseudopotential), which CP2K setting removes it, and whether
  the higher Fe/N errors in Na frames have the same cause.
- Proposed path: settle the cause with a translation test on one frame before relabelling
  anything ("Proposed work" below).

## Evidence
### 1. Model errors (`pb_mace_v2` on `valid.xyz`)
Source: `runs/pb_mace_v2-valid/errors/errors.tsv` (job 11750727, not registered). Force
RMSE overall 73.5 meV/Å, 47.2 without Na atoms (journal 2026-11-19).

Split by frames with and without Na (2026-11-20, from `runs/pb_mace_v2-valid/eval.xyz`):

| Element | Force RMSE, frames without Na (meV/Å) | Force RMSE, frames with Na (meV/Å) |
|---|---|---|
| H | 16.3 | 22.5 |
| C | 26.8 | 44.3 |
| N | 29.3 | 81.1 |
| O | 35.0 | 48.4 |
| Fe | 40.2 | 99.0 |
| Na | — | 390.1 |

In the Na frames the other elements have 1.4–2.8× the error they have in frames without Na.
That is not explained yet. The frames without Na come from other systems (water, vacancy
cells), and the grid fit (section 3) gives ≤ 0.04 eV/Å on the other elements.

### 2. Net force of the reference labels
Exact forces on a periodic cell sum to zero (translation invariance); MACE forces do so by
construction. Reference labels of `train.xyz` + `valid.xyz` (2026-11-20). |ΣF| is the norm
of the summed force of a frame; |F| is the absolute value of one Cartesian component:

| config_type | Na per frame | Atoms | Cell (Å) | Frames train/valid/test | Median \|ΣF\| (eV/Å) | Median \|F\| Na (eV/Å) | Median \|F\| others (eV/Å) |
|---|---|---|---|---|---|---|---|
| cubo_puro | 4 | 60 | 10.170 cubic | 235/27/20 | 1.05 | 0.24 | 0.43 |
| cubo222 | 24 | 530 | 20.340 cubic | 101/20/0 | 3.15 | 0.29 | 0.44 |
| interface_N3 | 8 | 267 | 10.087² × 36.002 | 158/22/13 | 1.68 | 0.28 | 0.47 |
| interface_W4a | 8 | 267 | same | 171/38/13 | 1.71 | 0.29 | 0.48 |
| interface_W4aTS | 8 | 267 | same | 51/0/0 | 1.65 | 0.26 | 0.47 |
| interface_W4aTSr | 8 | 267 | same | 46/0/0 | 1.77 | 0.26 | 0.48 |
| interface_W4b | 8 | 267 | same | 149/12/13 | 1.66 | 0.29 | 0.47 |
| interface_W4bTS | 8 | 267 | same | 50/13/0 | 1.71 | 0.28 | 0.48 |
| interface_W4bTSr | 8 | 267 | same | 64/0/0 | 1.64 | 0.30 | 0.48 |
| interface_aimd | 8 | 267 | same | 29/0/0 | 1.37 | 0.25 | 0.40 |
| interface_longa | 8 | 267 | same | 87/18/0 | 1.59 | 0.26 | 0.45 |

Frames without Na: median |ΣF| 0.16–0.18 eV/Å (`vacancia_*`, 85 atoms) and 0.41–0.45 eV/Å
(`agua_*`, 384 atoms). In `valid.xyz` the net reference force equals the sum of the Na
residuals of the model (median cosine 0.986; `docs/rdf-mlmd-vs-aimd.md`, limit 7).

### 3. Periodicity with the grid (2026-11-19; `docs/rdf-mlmd-vs-aimd.md`, limit 7)
- The Na residual (reference − model) is periodic in the absolute Na position. A scan of
  the grid size N fits best at exactly 162, 576 and 324 points, the 700 Ry grid sizes of
  these cells, on all 9 cell axes. R² is 0.54–0.74 there, against a median of 0.004–0.06 at
  other N. Amplitude 0.45 eV/Å on Na, ≤ 0.04 eV/Å on the other elements.
- The amplitude (0.45 eV/Å) exceeds the typical reference Na force component (median
  0.24–0.30 eV/Å, section 2), which is why the model reproduces so little of it (slope 0.18).
- The AIMD (400/60) has it too: the Na positions of its frames are non-uniform modulo the
  400 Ry grid (best N 125, 450, 256).
- Grid spacing L/N (computed 2026-11-20): 0.062–0.063 Å at 700 Ry (N 162, 324, 576) and
  0.080–0.081 Å at 400 Ry (N 125, 256, 450). Limit 7 quotes 0.083 Å for the ripple
  period, which matches neither grid. Recheck it when the fit is redone.
- The 2026-11-19 fit scripts were in that session's scratchpad and are lost (checked
  2026-11-20), so this section cannot be rerun. The translation test below measures the
  same error directly, without a model.

## What is affected
- **Frames**: 1350 of 3047 (train 1141, valid 150, test 59).
- **Sources on neumann** (`origem` column of `data/consolidado/frames.tsv`, relative to
  `~/prussian-blue/cubo/dataset/`; legacy, read-only, ADR-0008):

  | Source | Frames |
  |---|---|
  | `cubo-puro-new/rotulagem/{b*,cadeias/k*}/relabel.out` | 282 |
  | `cubo222-new/rotulagem/{b*,cadeias/k*}/relabel.out` | 121 |
  | `interface-1np-new/rotulagem/{b01,estrela,semente}/relabel.out` | 29 |
  | `interface-1np-new/longa/rotulos/b*/relabel.out` | 105 |
  | `eventos/interface-1np/{N3,W4a,W4aTS,W4aTSr,W4b,W4bTS,W4bTSr}/rotulos/j*/[parcial_*/]relabel.out` | 813 |

- **AIMD reference** (400/60): the same kind of error moves the Na in the reference
  dynamics, and relabelling does not change those trajectories. The RDF doc argues that
  the ripple does not bias g(r) peaks at the 0.1–1 Å scale. That is an argument, not a test.
- **Claims**:
  - ID-1 and ID-2 (pending): their Na errors measure the labels more than the model. The
    owner still has to decide whether to add this limit to both.
  - ID-3 (pending): its Na group rests on these labels and on the AIMD (limit already
    listed).
  - A relabelled dataset means a new model and new claims (ADR-0013); the current claims
    stay as they are.
- **Training**: the Na label noise sets the floor of the validation loss (journal
  2026-11-19), so it also weighs on early stopping and model selection.

## Not known
- TODO(owner): Na basis set and pseudopotential in the qz input (`relabel.out` header or
  its input file) and in the AIMD `aimd.inp`.
- TODO(owner): grid settings of the qz input beyond 700/70 and "EPS 1e-6": `NGRIDS`,
  `&XC_GRID`, and which EPS that is.
- TODO(owner): the CP2K version behind the qz labels. The production module on neumann is
  `cp2k/2024.1-gcc-12.2.0-iy4ur5k` (`configs/machines/neumann.yaml`).
- TODO(owner): CP2K wall time per frame of the qz labels, per system (from the timing at
  the end of `relabel.out`). Needed for a relabelling cost estimate.
- Whether the Fe/N excess in Na frames (section 1) is label error too.

## Proposed work on neumann
This is a proposal: each step needs the owner's ok, and every job is asked first (ADR-0005).
0. **Scope.** Dataset labelling and CP2K runs are out of scope now (CLAUDE.md, Project;
   owner, 2026-11-17). A relabel changes that, so it needs the owner's decision and then an
   ADR for the new labelling protocol (a general choice, ADR-0013).
1. **Read, no runs.** The qz and AIMD inputs, to fill in the "Not known" items.
2. **Translation test** (a test job, exempt from the reading rule).
   - Frames: one `cubo_puro` frame (60 atoms, 4 Na), plus one `vacancia_*` frame (85 atoms,
     no Na) as the control. Both with the qz settings.
   - Shift: each frame rigidly by k·h/4 along x (k = 0…3, h = L/N = 0.0628 Å for cubo_puro
     at 700 Ry).
   - Measure: per element, the spread of the forces over the shifts, and |ΣF|. Exact
     forces do not change under a rigid shift, so both measure the grid error directly.
   - Expected if the diagnosis holds: a Na spread close to the 0.45 eV/Å amplitude, small
     on the other elements and in the control.
3. **Same test with candidate remedies**, one change at a time.
   - Candidates (not verified here; check them against the manual of the CP2K version in
     use): a higher CUTOFF/REL_CUTOFF; `&XC_GRID` smoothing (`XC_SMOOTH_RHO`, `XC_DERIV`)
     or `USE_FINER_GRID`; another Na basis/pseudopotential.
   - Hypothesis, to check against step 1: a semicore Na pseudopotential has a hard density
     that the grid represents poorly.
   - TODO(owner): the reduction that counts as "fixed", set before the test runs (e.g. Na
     spread and |ΣF| at the level of the control).
4. **Consistency.** It decides which frames to relabel.
   - A Na-only change (basis or pseudopotential): relabel all 1350 Na frames, so that there
     is one protocol per element. The fitted E0s absorb a constant Na shift.
   - A global change (cutoff, XC grid) changes every label. Then either relabel all 3047
     frames, or show on control frames that the non-Na labels change less than a
     tolerance set beforehand.
5. **Cost.** Frames × time per frame (step 1), in core-hours (neumann's unit). CP2K
   cannot run on n01–n08, and n09 kills CP2K after ~11–13 h (`neumann.yaml`).
6. **Output.** A new dataset version: same frames, split and groups, new `REF_*` for the
   relabelled frames, a new MANIFEST and sha256. Then a new model on SDumont, with its
   dataset version, split and hyperparameters fixed before training (ADR-0013).

**Without CP2K** (weaker options, if relabelling costs too much):
- Down-weight the Na forces in training. This needs per-atom force weights for Na only.
  TODO: check whether the MACE version in `mace_env` supports them. Per-frame weights
  would also drop the Fe/C/N forces of 44 % of the data.
- Subtract ΣF/N_Na from each Na force. That removes only the mean of the error, not the
  per-atom ripple.
- In both cases the Na dynamics stay unlearned.

## Translation test (set up 2026-11-20, neumann)
- Prep `scripts/prep_na_translation.py`, config `configs/na_translation/translation_test.json`
  (`fe35fc2`), run dir `runs/na-translation-test/` (7 jobs, n12, 28 MPI x 2 OpenMP).
- Frames (train): cubo_puro b01 #1 (60 atoms, 4 Na); control vacancia c01 #1 (85, no Na).
- Shifts: x by k*h/4, k = 0..3, h = cell/N (N read from the output).
### Reading (fixed before submission; a test, exempt from the claim rule)
- s_el: RMS over the atoms of el and the 3 components of the std of the force over the
  valid shifts (meV/Å). |ΣF|max: largest norm of the summed force over the shifts.
  Valid shift: every Fe Mulliken spin within 0.3 of shift 0 (pb_conv.py default);
  fewer than 3 valid shifts -> that run is inconclusive.
- Check: shift 0 of cubo_puro-q9-c700 reproduces the legacy label (max |ΔF| ≤ 10 meV/Å),
  else the whole test is inconclusive.
- Diagnosis (cubo_puro-q9-c700): confirmed if s_Na ≥ 100 meV/Å and
  s_Na ≥ 5 × max(s_Fe, s_C, s_N); refuted if s_Na < 50 or s_Na < 2 × that max;
  otherwise inconclusive.
- Remedy (each other cubo_puro setting): "fixed" if s_Na ≤ 2 × max_el s_el and
  |ΣF|max ≤ 2 × |ΣF|max, both of vacancia-q9-c700 (the quality of today's non-Na labels).
- No verdict, reported only: s_el and |ΣF| vs cutoff; q1 vs q9-c1600 forces at shift 0
  (a first look at q1 physics, not a validation); vacancia-q9-c400 (AIMD setting).

## Translation test v2 (set up 2026-11-20, neumann)
- Why: v1 was inconclusive by its own rule: shift 0 of cubo_puro-q9-c700 missed the legacy
  label by max |ΔF| 266.5 meV/Å (limit 10), its Fe spins 0.099 from the label's; shifts of
  q9-c700 and q9-c1200 changed state (ΔE −270, −367 meV) inside the 0.3 spin gate.
- Prep `scripts/prep_na_translation_v2.py`, config `configs/na_translation/translation_test_v2.json`
  (`d1af820`), run dir `runs/na-translation-test-v2/`; jobs 4392–4397 (n12, 28 MPI x 2
  OpenMP), submitted 2026-11-20 16:02.
- Each of 8 shifts (x by k*h/8, k = 0..7) is its own single point from one seed wavefunction,
  full U from the first SCF step. Seeds: v1 outputs in the label's state (Fe spins within
  0.001 of the label): cubo_puro-q9-c1600, vacancia-q9-c700; q1: generated in the job from
  the unshifted frame with the label protocol (`seed_gen/`).
- Settings: cubo_puro q9 at 700, 1600, 2000, 2400 Ry (REL_CUTOFF 70) and q1 at 700;
  control vacancia q9 at 700.
### Reading v2 (fixed after submission, before any output was read; a test, exempt from the claim rule)
- s_el and |ΣF|max: as v1, over the valid shifts.
- Valid shift: every Fe Mulliken spin within 0.01 of the reference state: the legacy label
  (q9 runs) or the run's `seed_gen` output (q1). Fewer than 6 valid shifts -> that run is
  inconclusive.
- Check: shift 0 of cubo_puro-q9-c700 reproduces the legacy label (max |ΔF| ≤ 10 meV/Å),
  else the whole test is inconclusive.
- Diagnosis (cubo_puro-q9-c700) and Remedy (each other cubo_puro run vs vacancia-q9-c700):
  the v1 thresholds, unchanged.
- No verdict, reported only: s_el and |ΣF| vs cutoff; q1 vs q9-c2400 forces at shift 0;
  Fe spins of the q1 `seed_gen` vs the label's; per-shift energies.
- Analysis: `src/na_translation.py` reads the v1 layout only; the v2 layout (`shift_K/`)
  goes in, with a test, before any output is read.

## Handoff
- Read first: this doc; `docs/rdf-mlmd-vs-aimd.md`, limit 7; journal 2026-11-19.
- Dataset on neumann: `~/prussian-blue/cubo/dataset/consolidado/` (sha256 in journal
  2026-11-17).
- Legacy dirs are read-only: copy inputs into a run dir under `runs/` of the neumann clone
  (`/home/eudes/pb-mace-store/runs`) before any test.
- The tables of sections 1 and 2 came from session scratchpad scripts that were not kept.
  If they are needed again, they go into `src/` with a test.
