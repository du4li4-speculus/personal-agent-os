---
artifact: adr
version: "1.0"
created: 2026-09-04
status: accepted
---

# ADR-0001: Reconcile Repository States Without History Loss

## Status

Accepted on 2026-09-04. The repository owner approved the v0.3+ implementation plan and its preservation-first sequence.

## Context

The repository began the upgrade with three valid states: GitHub `main` at `3176353` containing Cognition and governance documents, local commits `ce9c8cf` and `ce80768` containing the Runtime foundation, and uncommitted TOEFL Skill source plus instance output. Selecting one state by reset, clean, rebase, or overwrite could lose source or history. Instance output must not enter Git.

## Expansion

| Option | Scalability | Complexity | Migration risk | Maintenance cost |
| --- | --- | --- | --- | --- |
| Keep local state only | Low; remote governance remains absent | Low | High loss of accepted remote work | High divergence from GitHub |
| Preserve local source, then merge verified GitHub `main` | Supports the current platform path | Medium | Low when source is committed first | Low; one auditable history |
| Rebuild in a fresh repository or worktree root | Potential multi-project flexibility | High | Critical copy and provenance risk | High duplicated history and configuration |

## Critique

- A local-only choice makes local Runtime history another source of truth.
- A fresh rebuild duplicates repository identity and risks omitting untracked TOEFL source.
- A merge before preserving the dirty worktree makes conflict recovery unsafe.
- Broad staging can capture student output or macOS metadata.

## Decision

We will create `codex/agent-os-v0.3-plus`, commit the complete source-only local state with explicit path staging, verify the exact GitHub `main` SHA, and merge `origin/main` with `--no-ff`. We will not reset, clean, rebase, force-push, delete output, or stage `skills/*/output/`.

## Rejected alternatives

- Keep local only: rejected because it drops accepted Cognition and governance work.
- Reset local to GitHub: rejected because it discards Runtime commits and uncommitted Skill source.
- Rebase local commits: rejected because the plan requires preserving both histories without rewriting them.
- Fresh repository reconstruction: rejected because it increases migration and provenance risk without solving an observed boundary problem.

## Consequences

### Positive

- Every legitimate source state remains recoverable in Git history.
- Remote and local provenance is visible in one integration branch.
- Run data remains outside the commit.

### Negative

- The branch contains an explicit merge commit and a larger source-preservation commit.
- Future readers must consult the repository-state record to understand the three inputs.

### Neutral

- No push or merge to GitHub `main` is authorized by this decision.

## Future changes enabled

Later contract and Runtime upgrades can start from one clean, auditable repository state rather than choosing between competing histories.

## References

- `docs/REPOSITORY_STATE.md`
- `docs/AGENT_OS_ARCHITECTURE_REVIEW.md`
- `docs/superpowers/plans/2026-09-04-agent-os-architecture-upgrade-v0.3-plus.md`
