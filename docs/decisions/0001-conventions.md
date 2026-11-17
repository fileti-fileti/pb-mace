# 0001. Repo conventions and decision process
- Status: Accepted (2026-11-17). Decision process and research rule 1 superseded by
  [0013](0013-lighter-decision-process.md).
- Date: 2026-11-13. Decided by: owner (Eudes Fileti), proposed by the agent.

## Context
The repo follows `mini-lab-repo-guide.md` (normative), adapted to two machines with
mutually exclusive VPNs. The owner adjusted parts of the guide during setup (F0).

## Decision
**Layout and records** as in the guide: status block in `CLAUDE.md`, append-only journal,
ADRs, claims, registered results, cost ledger, glossary, verified `.bib`. Data, run outputs
and large files never in git (pre-commit hook).

**Two-machine adaptations**
- Journal titles carry the machine: `## YYYY-MM-DD — <machine> — <title>`.
- One status block, with one "last sync" line per machine (commit hash + date).
- `/start-session` also detects the machine, checks that machine's Slurm queue, divergence
  from the hub and that machine's purge dates.
- Personal preferences live in `~/.claude/CLAUDE.md` per machine; the repo `CLAUDE.md`
  holds project rules only.
- Mechanical ask-first via `.claude/settings.json` (ask: `sbatch`, `scancel`, `git push`;
  deny: force-push, `rm -rf`).

**Template scope**: project parts of the guide (`docs/<experiment>.md`, `docs/claims.md`,
step 6) exist only as skeletons. The research question is asked in the documented
"new project from template" procedure, not here.

**Decision process** (owner's adjustment; diverges from the guide, which asks teach-back for
every design decision):
- Research/methodology decisions (reading rules, claims, comparisons, metrics): full
  teach-back; the owner's words are pasted here.
- Infrastructure decisions (layout, ssh, sync, ledger, naming): the agent explains in ~2
  lines, the owner answers "approved"; the ADR records the approval and the agent's
  justification.
- Ask only what blocks the next step; the rest becomes `TODO(owner)` and the most
  conservative default is used.

**Research rules** (from the guide; need teach-back):
1. The reading rule (question, metric, threshold, yes/no) is fixed in the experiment doc and
   as a *pending* claim before any run whose result will support a claim or a comparison;
   never changed after results are seen; a changed rule makes a new claim. Benchmarks,
   dataset generation/labelling, tests and toy jobs are exempt, but remain under ask-first.
2. A number not in `docs/claims.md` is not stated; claim numbers come from registered files
   or a report script run on them.
3. Fair comparisons: same model and same compute per run; validation from the training side
   only; test data never influence a choice.

## Owner's explanation (verbatim) or approval, and agent's check
- Infrastructure parts and decision process: approved by the owner, 2026-11-13 (setup F0).
  Agent's justification: keeps the guide's audit trail while not slowing infra work with
  teach-back on choices that carry no scientific risk.
- Research rules: accepted by the owner under ADR-0013 (2026-11-17), without teach-back;
  rule 1 read there for model tests and MLMD vs AIMD comparisons.

## Consequences
- Every later ADR states which process it went through.
- Until the research-rules teach-back, no experiment doc or claim is written (lifted by
  ADR-0013, 2026-11-17).
