# Na relabelling with the q1 protocol

ADR-0016 (protocol) and ADR-0015 (scope). Background: `docs/na-label-grid-error.md`.
Machine: neumann. Legacy directories are read-only (ADR-0008): every input is copied into
a run dir under `runs/`.

## Protocol
- Each frame's legacy qz input (`relabel.inp` of its `origem` in
  `consolidado/frames.tsv`) gets only these edits:
  - the Na KIND: `BASIS_SET TZVP-MOLOPT-PBE-GTH-q1` from `BASIS_MOLOPT_UZH`, and
    `POTENTIAL GTH-PBE-q1` from `POTENTIAL_UZH`, both in the CP2K 2024.1 data dir;
  - the seed of the electronic state (below).
- Everything else stays at qz: 700/70, UKS, CHARGE, MULTIPLICITY, U 6 eV on Fe3, D3(BJ),
  EPS_SCF.
- State: the labels hold the ferromagnetic state of their legacy run. A relabel counts only
  if every Fe Mulliken spin is within 0.01 of the frame's legacy label (as in translation
  test v2).

## Cost (agent's estimate, 2026-11-25)
- Legacy per-frame wall times, read from the legacy `relabel.out` files on 2026-11-25
  (scratchpad script, not kept):

  | Source | Na frames | Legacy time per frame |
  |---|---|---|
  | cubo-puro | 282 | 233 s, 56 MPI |
  | cubo222 | 121 | 2224 s, 56 MPI |
  | interface-1np rotulagem + longa | 134 | 509 s, 96 MPI |
  | eventos/interface-1np | 813 | 718–1092 s, 128 MPI |

- At 700 Ry this totals 27.8–38.6k core-h. With q1 (×1.2, translation test v2) it is
  33–46k core-h, or 3–4.3 days of the whole n12 (448 cores).

## Phases (owner's "ok", 2026-11-25)
1. The q1 check (below), ~1.5–4.3k core-h.
2. Phase 1: the 537 Na frames outside the events (cubo_puro 282, cubo222 121,
   interface_aimd + interface_longa 134), ~8.4k core-h. Then a retrained model shows
   whether the Na force error drops.
   - TODO(agent): fix that reading rule before the training.
3. Phase 2: the 813 event frames, ~25–38k core-h.

## q1 check (a test of the labelling protocol, exempt from the claim rule; rule fixed before it runs)

### Question
Do the q1 labels at 700/70 give the same relative energies of interface-1 configurations
as the converged semicore reference, Na q9 at 2000/70?

### Design
- **Frames.** 12 frames of interface-1np from the train split, in four strata of 3:
  - EQ = `interface_longa`;
  - N3 = `interface_N3` (Na260 leaving a face octant for the solution);
  - W4 = `interface_W4a` and `interface_W4b` (water permeation windows);
  - TS = `interface_W4aTS`, `_W4aTSr`, `_W4bTS` and `_W4bTSr`.
- **Eligibility.**
  - The `origem` path has no `parcial_*` part, and its directory has no `parcial_*`
    subdirectory (restarted label jobs).
  - `interface_aimd` is excluded: its labels started from the atomic guess, while all
    the others started from the seed `eventos/interface-1np/base/chute.wfn`.
- **Draw.** `random.Random(20261125)`. For each stratum, in the order EQ, N3, W4, TS:
  `sample(eligible rows sorted by i, 3)`. The prep script makes the draw and records it.
- **Base input.** The `relabel.inp` of the first drawn frame's `origem`.
  - The prep checks that every drawn `origem` has the same `relabel.inp` except SEED,
    STEPS and LAST_SNAPSHOT, and the same kind column in `COORD.inc`.
  - Every setting starts each snapshot from its seed with the full U, as the longa and
    event labels did: SCF_GUESS RESTART, U_RAMPING 0, EXTRAPOLATION USE_GUESS.
- **Settings.** One run dir per setting: REFTRAJ over a pool of the drawn snapshots,
  copied from the legacy `pool_lote.xyz`.

  | Setting | Role | Frames | Seed |
  |---|---|---|---|
  | q9-c700 | reproduction check | first drawn EQ and first drawn TS | `chute.wfn` (copied) |
  | q9-c2000 | reference | 12 | `chute.wfn` (copied) |
  | q1-c700 | protocol | 12 | q1 seed |
  | q1-c2000 | control: pseudopotential effect without the grid | 12 | q1 seed |

- **q1 seed.** A separate job, run and checked first. It is one SCF on the first drawn EQ
  frame with q1 at 700/70, using the `interface_aimd` label protocol (SCF_GUESS ATOMIC,
  U ramping 0.5 eV each SCF).
- **Layout.** 96 MPI × 1 thread on n12, partition EPYC_9734. That is the layout of the
  legacy interface labels: the `GLOBAL|` lines of their `relabel.out`, launched by
  `~/prussian-blue/cubo/dataset/roda_fila_rotulos.sh`.
- **Cost.** Per frame, 700 Ry costs 13.6–39 core-h (legacy timings above). Assuming the v2
  ratios (×3.8 for 2000 Ry, ×1.2 for q1), the check costs ~1.5–4.3k core-h. Dropping
  q1-c2000 would cut it to ~0.9–2.5k.

### Reading rule (fixed 2026-11-25, before any input is prepared)
- **Valid frame.** In each of q9-c2000, q1-c700 and q1-c2000, the SCF converged and every
  Fe Mulliken spin is within 0.01 of the frame's legacy label.
  - Fewer than 9 valid frames make the test inconclusive.
- **Checks.** Any failed check makes the whole test inconclusive.
  - The q1 seed's Fe spins are within 0.01 of the seed frame's legacy label.
  - Each q9-c700 frame reproduces its legacy forces within max |ΔF| ≤ 10 meV/Å.
- **Metric.** E_i^s is the total energy of frame i in setting s, and
  ΔE_i^s = E_i^s − mean over the valid frames of E^s.
  - D(A, B) = max over the valid frames of |ΔE_i^A − ΔE_i^B|.
  - kT = 25.9 meV (300 K).
- **Verdict.**
  - **yes** (q1 adopted, ADR-0016 holds): D(q1-c700, q9-c2000) ≤ kT.
  - **no** (q1 rejected, ADR-0016 superseded): otherwise, if D(q1-c2000, q9-c2000) > 2 kT.
  - **inconclusive**: otherwise. The owner decides from the reported numbers.
- **Reported only.**
  - D(q1-c700, q1-c2000), the host grid at 700 Ry.
  - D per stratum.
  - RMS and max |ΔF| per element for the three pairs.
  - |ΣF| per frame and setting.
  - Fe spin differences, SCF steps and wall time per frame.

### How to run
- Prep: `scripts/prep_na_q1_check.py configs/na_relabel/q1_check.json --name na-q1-check`
  (draw, inputs, seeds, jobs; tests in `tests/test_prep_na_q1_check.py`). It needs a clean
  tree, and the run records its commit.
- Analysis: `python3 src/na_q1_check.py runs/na-q1-check` (this rule; tests in
  `tests/test_na_q1_check.py`).
- Jobs: ask first. The q1 seed job runs before the others.

### Results
- Pending.
