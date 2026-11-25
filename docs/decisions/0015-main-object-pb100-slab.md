# 0015. Main MLMD object: the PB(100)/water slab; Na relabelling in scope
- Status: Accepted.
- Date: 2026-11-25. Decided by: owner (Eudes Fileti), proposed by the agent. Process:
  simulation protocol and scope (ADR-0013).

## Context
- On 2026-11-21 the owner approved ("ADR ok") an ADR-0015 that made the nanocube the main
  MLMD object (journal 2026-11-21). It was never written. Its open problem: ~36 of the
  nanocube's 116 Fe sit in edge motifs that are absent from training (journal 2026-11-21),
  so it needed edge data or a committee.
- The Na force labels carry a CP2K grid error (`docs/na-label-grid-error.md`). Translation
  test v2 confirmed it on 2026-11-25 and found remedies (ADR-0016, `docs/na-relabel.md`).
- The interface-1 cell of the dataset (`interface_*`: 267 atoms, 10.087 × 10.087 × 36.002 Å,
  8 Na) is already a periodic PB(100) slab with water on both faces. Agent's check on
  2026-11-25, first `interface_aimd` frame of `train.xyz`:
  - 4 Fe planes at z ≈ −1.1, 3.9, 9.0 and 14.0 Å; water at z ≈ 15–33 Å.
  - Surface Fe(III) carry 5 N + 1 water O; surface Fe(II) carry one pendant CN. Both
    motifs are covered in training.
- Literature (agent's web search, 2026-11-25; not a formal bibliographic check): it found no
  MLFF study and no ns-scale AIMD study of a Prussian-blue or PBA/water interface with Na.
- interface-2 (111): a legacy AIMD exists (`~/prussian-blue/cubo/dataset/interface-2`:
  687 atoms, no Na, antiferromagnetic, 400/60 Ry), with an unlabelled pool of 450 snapshots.
  - By the agent's formal-charge count, a neutral Na-free cell puts every Fe in Fe(III).
    That is another redox state than interface-1, and its magnetic order differs from the
    ferromagnetic qz labels.
  - Its (111) surface is polar.

## Decision
- The main MLMD object is the PB(100)/water slab, two interfaces per cell, built as lateral
  supercells of the interface-1 cell. The first is 3×3 (`configs/mlmd/slab100_test.json`).
- The nanocube is dropped as the main object. Its approved ADR was never written, and this
  ADR replaces it.
- Na relabelling enters the scope:
  - CP2K single points on neumann for the 1350 Na frames, with the protocol of ADR-0016,
    in two phases (`docs/na-relabel.md`).
  - Other dataset generation stays out of scope: no new AIMD.
- interface-2 (111) is out of scope for now. It is reconsidered after the first (100) slab
  results.

## Approval and agent's check
- Owner, 2026-11-25 (verbatim): "Pensei se em vez de simular um nanocristal finito, nao
  seria interessante simular uma interface infinida em 2D, uma slab, com agua dos dois
  lados da caixa (duas interfaces numa mesma célula)."
- Then: "vamos. preparar a slab, e fazer alguns testes iniciais. em paralelo vamos focar na
  nova rotulacao para resolver o problema do sódio."
- Then "ok", answering the agent's five proposals, of which this ADR was one.
- Agent's justification:
  - The slab supercells contain only environments present in training: no edges, and the
    same water thickness as the training cell.
  - The Na label error stays on the critical path, because every interface frame has 8 Na.

## Consequences
- The 3×3 slab has 2403 atoms, a 30.261 × 30.261 × 36.002 Å cell and Fe2/Fe3 = 72/72
  (agent's build check, 2026-11-25). Its lateral edge exceeds twice the 12 Å receptive
  field.
- First tests run on SDumont (ask first): `prep_mlmd.py --check` and a short NVT.
  - With `pb_mace_v2` they test stability, cost and water structure, not the Na physics.
- A paper also needs thicker water and convergence tests in slab thickness and lateral
  size. Not decided.
- The interface-1 AIMD (400/60 Ry, Na q9) has a larger Na grid error than the labels, so
  validating the Na structure needs another reference. Open.
- Changed with this ADR: `CLAUDE.md` (Project, status block), `docs/decisions/README.md`.
  The nanocube tasks leave the status block.
