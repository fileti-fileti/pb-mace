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
- Evidence: pending
- Method: `docs/mace-training.md`. Jobs: pending. Cost: pending
