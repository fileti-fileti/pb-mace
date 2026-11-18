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
