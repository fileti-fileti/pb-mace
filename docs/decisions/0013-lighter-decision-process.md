# 0013. Lighter decision process: the owner's ok replaces the teach-back
- Status: Accepted. Supersedes the decision process and research rule 1 of
  [0001](0001-conventions.md).
- Date: 2026-11-17. Decided by: owner (Eudes Fileti), proposed by the agent. Process:
  infrastructure (approval).

## Context
ADR-0001, inherited from lab-template, asks for a teach-back on every research or
methodology decision and stays Proposed until the owner gives it for the research rules;
until then no experiment doc or claim can be written. In hidrotopia-co2 the owner replaced
the teach-back with a lighter process (hidrotopia-co2 ADR-0017, 2026-11-16) and accepted
ADR-0001 with it. This project adopts the same process, with the research rules read for
MLFF training and MLMD. lab-template itself is unchanged; carrying the change there is a
separate decision.

## Decision
1. No teach-back. The agent proposes each decision in 2–3 lines (what and why); the owner
   answers "ok" or "approved"; the record keeps that answer and the agent's justification.
2. An ADR only for general choices about physics, training or simulation protocol,
   analysis method or repo infrastructure. Experiment-specific choices (dataset version,
   split, hyperparameters, run lengths, reading rules) go in the experiment doc; small
   choices go in the journal entry (Decisions).
3. The research rules of ADR-0001 stay, as rules the agent applies. Rule 1 reads:
   - Model test (descriptive: errors of a model on the test set): before the model is
     trained, the experiment doc fixes the dataset version (sha256), the
     train/validation/test split and how it is drawn, and the hyperparameters; before the
     test set is evaluated, it fixes the metrics and the threshold that counts as pass.
   - MLMD vs AIMD (comparative: RDFs): before the MLMD output is analysed, the doc fixes
     the systems, the MLMD protocol and length, the RDF parameters (pairs, r range, bin
     width, discarded initial time), how the error is computed and when MLMD and AIMD
     count as agreeing; outcomes yes, no or inconclusive.
   - The rule is never changed after the results are seen; a changed rule makes a new
     claim.
   Rule 2 (a number is stated only from a claim built on registered results) is unchanged.
   Rule 3 (fair comparisons) reads: models compared get the same training data, split and
   compute; validation (early stopping, model selection) uses the training side only; the
   test set never drives a choice; MLMD and AIMD RDFs are computed with the same analysis
   parameters.
4. ADR-0001 becomes Accepted with these changes.

## Approval and agent's check
- Owner, 2026-11-17 (verbatim): "Aprovado!", answering this proposal.
- Agent's justification: the same process the owner already runs in hidrotopia-co2; it
  keeps the safeguard that protects the results (rules fixed before the data are seen,
  test set never used for a choice) and removes the step that blocked experiment docs.

## Consequences
- Experiment docs and claims are no longer blocked.
- Changed with this ADR: `CLAUDE.md` (Hard rules, Task loop), ADR-0001 status,
  `docs/decisions/README.md`, the glossary entry for teach-back.
- The project's decision process differs from lab-template's.
