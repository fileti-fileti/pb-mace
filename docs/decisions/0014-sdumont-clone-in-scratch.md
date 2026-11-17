# 0014. SDumont clone in /scratch
- Status: Accepted. Supersedes the SDumont clone location of
  [0012](0012-github-origin-and-sdumont-locations.md), for this project.
- Date: 2026-11-17. Decided by: owner (Eudes Fileti), proposed by the agent. Process:
  infrastructure (ADR-0013).

## Context
ADR-0012 puts SDumont work clones in `$HOME` (`/prj/acmes/eudes.fileti3`, NFS, 250G) and
the store in `/scratch/acmes/eudes.fileti3/projects` (Lustre, purge rule unknown). The
owner prefers the clone in `/scratch`. Differences: SDumont's user documentation, as the
agent knows it, says compute nodes mount `/scratch` but not `/prj`, so job scripts that
read files from a clone in `$HOME` would fail (not verified on this account); a clone in
`/scratch` is exposed to the unknown purge rule.

## Decision
- The pb-mace clone on SDumont is `/scratch/acmes/eudes.fileti3/projects/pb-mace`; the
  store stays `/scratch/acmes/eudes.fileti3/projects/pb-mace-store`.
- `repo_parent` in `configs/machines/sdumont.yaml` becomes
  `/scratch/acmes/eudes.fileti3/projects`.
- Every SDumont session ends with `/end-session` (push), so a purge costs at most the
  commits since the last push; the clone holds nothing that is not in git (data, runs and
  logs are symlinks to the store).

## Approval and agent's check
- Owner, 2026-11-17 (verbatim): "Faz diferenca colocar o clone em HOME ou SCRATCH? Se
  nao, coloque no SCRATCH". Then "ok", answering this proposal.
- Agent's justification: repo and run files on the one filesystem the compute nodes see;
  the purge risk on a clone is bounded by GitHub.

## Consequences
- Check at the first SDumont toy job (ask first): the job reads a file from the clone and
  lists `/prj/acmes/eudes.fileti3`, which settles the compute-node mounts.
- The store's purge risk is unchanged (ADR-0012): anything irreplaceable also lives
  elsewhere.
- Changed with this ADR: `CLAUDE.md` (Project, status block), ADR-0012 status,
  `docs/decisions/README.md`, `configs/machines/sdumont.yaml`.
