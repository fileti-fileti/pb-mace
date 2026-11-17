# Glossary

One line per term.

- **ADR**: Architecture Decision Record, `docs/decisions/NNNN-*.md`; never edited once accepted, only superseded.
- **AIMD**: ab initio molecular dynamics (here CP2K); the reference for the MLMD RDFs.
- **Bare repo**: a git repo with no working tree; `origin` of the neumann repos created before ADR-0012.
- **Claim**: a statement in `docs/claims.md` with a reading rule fixed before the result.
- **Deploy key**: an ssh key with access to one GitHub repo only; one per (repo, machine) (ADR-0012).
- **Ledger**: `results/cost_ledger_<machine>.csv`, one row per ended job.
- **MACE**: the equivariant message-passing MLFF architecture trained in this project.
- **MLFF**: machine-learned force field; maps a structure to its energy and forces.
- **MLMD**: molecular dynamics driven by an MLFF.
- **RDF**: radial distribution function g(r) of an atom pair.
- **Reading rule**: question, metric, threshold and what counts as yes/no, fixed before a run.
- **Registered result**: verbatim copy under `results/<name>/` with `PROVENANCE.json` checksums.
- **Status block**: the part of `CLAUDE.md` between the STATUS markers; current state only.
- **Teach-back**: the owner explains a research decision in their own words before it is adopted; not used in this project (ADR-0013).
