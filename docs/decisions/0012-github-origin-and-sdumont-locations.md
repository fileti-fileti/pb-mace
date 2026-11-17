# 0012. GitHub as origin; SDumont locations
- Status: Accepted. Supersedes [0003](0003-sync-mac-hub.md), and the bare-repo clause and
  SDumont part of [0004](0004-locations-and-storage.md). SDumont clone location superseded
  by [0014](0014-sdumont-clone-in-scratch.md) (pb-mace).
- Date: 2026-11-13. Decided by: owner (Eudes Fileti). Process: infrastructure (approval).

## Context
ADR-0003 chose the Mac hub because the owner's GitHub account was inaccessible. It is
accessible now: from neumann, `git ls-remote` to a private repo works through a per-repo ssh
alias (2026-11-13); from SDumont, ssh to GitHub on ports 22 and 443 is open (setup F3,
2026-11-13). ADR-0004 left the SDumont repo location pending on the `/scratch` purge rule.

## Decision
- Each repo's `origin` is a private GitHub repo in the owner's account. New repos have no
  server bare repo and no Mac hub: each machine pulls from GitHub at `/start-session` and
  pushes to it at `/end-session`.
- Access: one deploy key per (repo, machine), write access, behind an ssh alias
  `github-<repo>` with `IdentitiesOnly yes`; no account-wide key on shared clusters.
- New projects start from the lab-template history (ADR-0002) and keep it reachable as the
  remote `template`.
- SDumont: work clones in `$HOME` (`/prj/acmes/eudes.fileti3`); store in
  `/scratch/acmes/eudes.fileti3/projects/<p>-store`, accepting the unknown purge rule.
- Repos created before this ADR (lab-template, sandbox and other neumann clones) keep their
  bare `origin` in `~/git/` until migrated.

## Owner's approval and agent's check
Owner, 2026-11-13 (verbatim): "esquece essa config adr0003 ja que agora o git esta
funcionando bem / pode deixar o repo parent no home / releva esse local bare ja que temos o
git de verdade agora / [...] A respeito do scrath aceito sim."
Agent's justification: both servers reach GitHub, so each machine syncs on its own without
switching VPNs and sees divergence itself; a deploy key leaked on a shared cluster exposes
one repo only.

## Consequences
- Lost guard: the bare repos' `receive.denyNonFastForwards`/`denyDeletes`. Remaining guard:
  `.claude/settings.json` denies force-push to the agent. TODO(owner): whether branch
  protection is available for a private repo on this account's plan.
- `/scratch` purge rule unknown: anything irreplaceable in an SDumont store also needs a
  copy elsewhere. TODO(owner): purge rule (helpdesk-sdumont@lncc.br).
- `template` remote on machines without `~/git/lab-template.git` (SDumont):
  TODO(owner): a private GitHub repo for lab-template; until then those clones have none.
- Changed with this ADR: `CLAUDE.md` (Two machines, status block), `docs/new-project.md`,
  both session skills, the glossary, `configs/machines/sdumont.yaml`.
