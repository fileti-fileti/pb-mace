# Decisions (ADRs)

Never edit an accepted ADR; write a new one that supersedes it and link both ways.
Status: Proposed → Accepted → "Superseded by NNNN".
Decisions need the owner's "ok" or "approved" plus the agent's justification; no
teach-back (ADR-0013, superseding that part of ADR-0001).

| ADR | Title | Status |
|---|---|---|
| [0001](0001-conventions.md) | Repo conventions and decision process | Accepted; decision process and rule 1 superseded by 0013 |
| [0002](0002-repositories.md) | Template repo plus one repo per project | Accepted |
| [0003](0003-sync-mac-hub.md) | Sync through the Mac hub with bare repos | Superseded by 0012 |
| [0004](0004-locations-and-storage.md) | Repo locations and large-storage symlinks | Accepted (neumann); bare repos and SDumont superseded by 0012 |
| [0005](0005-cost-and-ask-first.md) | Cost accounting and ask-first limits | Accepted (partial) |
| [0006](0006-language.md) | Language of docs and chat | Accepted |
| [0007](0007-python-environments.md) | Python environments recorded per machine | Accepted |
| [0008](0008-legacy-results.md) | Legacy work stays in place; registered as legacy-* | Accepted |
| [0009](0009-cost-ledger-per-machine.md) | One cost ledger file per machine | Accepted |
| [0010](0010-ledger-attribution-and-shared-extension-list.md) | Ledger attribution by WorkDir; shared blocked-extension list | Accepted |
| [0011](0011-workflow-and-tasks.md) | Session and task workflow; tasks live in the status block | Accepted |
| [0012](0012-github-origin-and-sdumont-locations.md) | GitHub as origin; SDumont locations | Accepted |
| [0013](0013-lighter-decision-process.md) | Lighter decision process: the owner's ok replaces the teach-back | Accepted |

## Template

```
# NNNN. <title>
- Status: Proposed | Accepted | Superseded by [NNNN](...)
- Date: YYYY-MM-DD. Decided by: <who>

## Context
## Decision
## Owner's explanation (verbatim) or approval, and agent's check
## Consequences
```
