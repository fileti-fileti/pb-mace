# Glossary

One line per term.

- **ADR**: Architecture Decision Record, `docs/decisions/NNNN-*.md`; never edited once accepted, only superseded.
- **AIMD**: ab initio molecular dynamics (here CP2K); the reference for the MLMD RDFs.
- **Bare repo**: a git repo with no working tree; `origin` of the neumann repos created before ADR-0012.
- **Block error**: standard error from contiguous blocks of frames; a lower bound when blocks are shorter than the correlation time.
- **Claim**: a statement in `docs/claims.md` with a reading rule fixed before the result.
- **Deploy key**: an ssh key with access to one GitHub repo only; one per (repo, machine) (ADR-0012).
- **E0s**: per-element isolated-atom energies that MACE subtracts from the total energy; here fitted by least squares (`E0s: average`), so only their sums over the training compositions are meaningful.
- **Fine-tuning**: training a model starting from the weights of a foundation model.
- **Foundation model**: a MACE model pre-trained on a broad dataset; here MACE-MP-0 small (`data/foundation/`).
- **Job chain**: a training job cut by its wall time that resubmits itself and continues from the latest checkpoint (`restart_latest`; `scripts/prep_mace_train.py`).
- **Ledger**: `results/cost_ledger_<machine>.csv`, one row per ended job.
- **MACE**: the equivariant message-passing MLFF architecture trained in this project.
- **MLFF**: machine-learned force field; maps a structure to its energy and forces.
- **MLMD**: molecular dynamics driven by an MLFF.
- **RDF**: radial distribution function g(r) of an atom pair.
- **qz**: the owner's CP2K labelling protocol: UKS PBE-D3(BJ), U 6 eV on Fe(III) only, cutoff 700/70, EPS 1e-6.
- **Reading rule**: question, metric, threshold and what counts as yes/no, fixed before a run.
- **Registered result**: verbatim copy under `results/<name>/` with `PROVENANCE.json` checksums.
- **Smoke run**: a short toy job that checks a run's setup end to end (data, env, GPU memory, time per epoch) before the real job; exempt from the reading rule.
- **Stitching**: joining the pieces of a restarted CP2K trajectory; the last branch through a step wins (`src/rdf.py`).
- **Status block**: the part of `CLAUDE.md` between the STATUS markers; current state only.
- **Teach-back**: the owner explains a research decision in their own words before it is adopted; not used in this project (ADR-0013).
