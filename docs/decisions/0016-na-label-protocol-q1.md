# 0016. Na label protocol: GTH-PBE-q1 at 700/70
- Status: Accepted, on the condition below.
- Date: 2026-11-25. Decided by: owner (Eudes Fileti), proposed by the agent. Process:
  physics and labelling protocol (ADR-0013).

## Context
Translation test v2 ran on 2026-11-25: `runs/na-translation-test-v2/`, jobs 4392–4397.
Its reading rule was fixed in `docs/na-label-grid-error.md`, and its numbers come from
`analysis/verdict.json`.
- **Diagnosis confirmed.** s_Na at q9-700 (today's labels) is 289.7 meV/Å, 28.9× the
  largest spread of the other elements. The reproduction check gave 0.53 meV/Å.
- **Remedies.** The limits were s_Na ≤ 28.1 meV/Å and |ΣF|max ≤ 529 meV/Å.

  | Setting | s_Na (meV/Å) | Verdict | Wall time vs q9-700 |
  |---|---|---|---|
  | q9-1600 | 33.4 | not fixed | 2.1× |
  | q9-2000 | 7.2 | fixed | 3.8× |
  | q9-2400 | 2.4 | fixed | 3.6× |
  | q1-700 | 0.0 | fixed | 1.2× (includes the q1 seed SCF) |

  Wall times are for the 8 single points of each run, on the same node and layout.
- **A higher cutoff changes the labels of every element.** Na frames at 2000 Ry mixed with
  Na-free frames at 700 Ry would carry two energy references per element. One E0 per
  element cannot absorb that, so all 3047 frames would need relabelling.
- **q1 changes the Na physics.** Reported only: at the unshifted cubo_puro frame, the RMS
  force difference between q1-700 and q9-2400 is Na 59.2, N 22.7, Fe 16.7 and C 11.4 meV/Å.

## Decision
- **Na protocol.** Na uses the GTH-PBE-q1 pseudopotential with the TZVP-MOLOPT-PBE-GTH-q1
  basis (CP2K data files `POTENTIAL_UZH` and `BASIS_MOLOPT_UZH`) at the qz setting 700/70.
  Every other element and every other qz setting stays unchanged.
- **Scope.** It applies to all 1350 Na frames. The 1697 Na-free frames keep their labels.
- **Condition.** The q1 check of `docs/na-relabel.md` (rule fixed before it runs) must say
  "yes". "No" supersedes this ADR; "inconclusive" returns the choice to the owner.

## Approval and agent's check
- Owner, 2026-11-25: "ok", answering the agent's proposal 1 ("Protocolo do Na = q1 a
  700/70 ... Só os frames com Na mudam; os 1697 sem Na continuam válidos").
- Agent's justification:
  - Of the tested remedies, q1 is the only one that changes Na alone. That keeps one
    protocol per element and leaves the other frames' labels valid.
  - It costs ~1.2× the qz label. q9-2000 costs 3.8× and would need every frame.

## Consequences
- Cost: ~33–46k core-h for the 1350 frames (`docs/na-relabel.md`, Cost).
- MULTIPLICITY is unchanged: going from q9 to q1 removes 8 electrons per Na, an even
  number.
- In the relabelled frames, the energy shifts by a constant per Na, which the fitted E0s
  absorb. Their host forces change by up to the amounts in Context.
- The labels follow the q1 model, not the semicore model. The q1 check bounds the
  difference only for the relative energies of interface frames.
