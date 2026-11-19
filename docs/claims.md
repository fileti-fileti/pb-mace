# Claims

A number that is not here is not stated. Status: final, provisional or pending; add
"negative" when the result went against the hypothesis. The rule is fixed before the
result and never changed afterwards; a changed rule makes a new claim.

```
### ID-1. <the claim, as a question or a statement> (status)
- Rule, fixed before the result: ...
- Numbers: copied from the registered files or from a report script run on them, never from memory
- Reading: what the rule says the numbers mean
- Limits: seeds, sizes, what was not tested
- Evidence: results/<name>/ and the command that prints the table
- Method: link to the doc section. Jobs: IDs. Cost: from the ledger
```

### ID-1. Test errors of the MACE model `pb_mace_v1` on the `consolidado/` test split (pending)
- Rule, fixed before the result (2026-11-17, `docs/mace-training.md`): RMSE and MAE of
  forces (meV/Å) and energy (meV/atom) on `test.xyz`, overall, per `config_type` and per
  element; descriptive, no yes/no threshold (owner's option (b)); fitness for the MLMD is
  decided by the RDF claim of `docs/rdf-mlmd-vs-aimd.md`.
- Numbers: pending
- Reading: pending
- Limits: one seed; test frames come from the same AIMD runs as the training frames
  (split by groups), so the test measures interpolation within these runs, not transfer.
  `test.xyz` has one group (11–20 frames) per config_type for 12 of the 20 types and no
  frame of cubo222, interface_aimd, interface_longa, vacancia_P1 or the TS windows
  (interface_W4aTS, _W4aTSr, _W4bTS, _W4bTSr) (`data/consolidado/frames.tsv`, checked
  2026-11-17, before the test evaluation): per-type errors are single-window estimates,
  and there is no test error for cubo222 or the interface-1 AIMD.
- Evidence: pending
- Method: `docs/mace-training.md`. Jobs: pending. Cost: pending

### ID-2. Test errors of the MACE model `pb_mace_v2` on the `consolidado/` test split (pending)
- Rule, fixed before the result (2026-11-18, `docs/mace-training.md`, pb_mace_v2): as
  ID-1: RMSE and MAE of forces (meV/Å) and energy (meV/atom) on `test.xyz`, overall, per
  `config_type` and per element; descriptive, no yes/no threshold.
- Numbers: pending
- Reading: pending
- Limits: as ID-1. v2 continues v1 (same seed and data), so v1 and v2 are not independent
  models. Which of the two goes to the MLMD is fixed by the validation loss, not by the
  test (`docs/mace-training.md`, pb_mace_v2).
- Evidence: pending
- Method: `docs/mace-training.md` (pb_mace_v2). Jobs: pending. Cost: pending

### ID-3. Does MLMD with `pb_mace_v2` reproduce the AIMD first-shell structure of cubo-puro, cubo222 and interface-1? (pending)
- Rule, fixed before any MLMD run (2026-11-19, `docs/rdf-mlmd-vs-aimd.md`; owner: "ok, no
  rascunho"; σ changed the same day, before any MLMD run, owner: "ok, faça tudo e estime a
  duracao do teste"): per pair, r1 (first-peak position; tolerance 0.05 Å) and n1
  (coordination number at the AIMD's first minimum; tolerance 5 % of the AIMD value); Δ =
  registered AIMD value − mean of 5 MLMD replicas, each as long as the AIMD; σ = s·sqrt(1
  + 1/5), s = spread of the replicas; yes if |Δ| + 2σ ≤ tolerance, no if |Δ| − 2σ >
  tolerance, otherwise inconclusive. One verdict per group (framework, water, Na) and
  system; a replica that loses atoms or gives non-finite values makes its system "no". g1
  (peak height) reported without a verdict.
- Numbers: pending
- Reading: pending
- Limits: frames of these AIMD runs are in the training set (reproduction, not transfer),
  and the MLMD starts from one of them; trajectories at 400/60, labels at 700/70; short
  AIMD (5–12 ps); σ has no floor from the AIMD's own error; CP2K grid (egg-box) error on
  Na in the labels and in the AIMD (limit 7 of the doc): Na dynamics not tested.
- Evidence: pending
- Method: `docs/rdf-mlmd-vs-aimd.md`. Model: `pb_mace_v2.model` (sha256
  0a38794dfde8bdf5de835c3a45e40b35b8bbdecbd5992c2dfb7ee57575c7f2f8), LAMMPS file
  `pb_mace_v2.model-lammps.pt` (sha256
  1bec51806daf555a8a12ff0cb0852a3507398372e3100f596dd0418c25ef45b0). Jobs: pending.
  Cost: pending
