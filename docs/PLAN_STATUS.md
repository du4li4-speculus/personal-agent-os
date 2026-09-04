# Plan Status

## Current authority

- `docs/AGENT_OS_ARCHITECTURE_EVOLUTION_v0.3_PLUS.md` - current normative architecture input
- `docs/AGENT_OS_ARCHITECTURE_REVIEW.md` - current repository review baseline
- `docs/superpowers/plans/2026-09-04-agent-os-architecture-upgrade-v0.3-plus.md` - current implementation plan

The v0.3+ plan is the only active implementation plan for this repository. Architecture-changing work must follow its Task order, commit boundaries, stop conditions, and review checkpoints.

## Historical inputs

- `docs/superpowers/plans/2026-09-03-toefl-agent-os-handoff-merge.md` - historical TOEFL handoff input; not an active repository-wide execution plan
- `docs/superpowers/plans/2026-09-03-toefl-agent-os-workspace-migration.md` - historical workspace migration input; its instruction that Runtime remain unchanged is superseded by the explicit v0.3+ architecture-upgrade request
- `docs/superpowers/plans/2026-09-03-agent-runtime-implementation.md` - completed Runtime implementation record
- `docs/superpowers/specs/2026-09-03-agent-runtime-design.md` - implemented Runtime foundation design

Historical documents remain unchanged for provenance. They do not override the current architecture directive, accepted ADRs, or v0.3+ plan.

## Precedence

1. Explicit current user instruction and stop conditions
2. Accepted v0.3+ architecture decisions and governance policies
3. Current v0.3+ implementation plan
4. Existing executable contracts and tests
5. Historical plans and migration notes

If two current authorities conflict, implementation stops until the conflict is reviewed. The conflict must not be resolved by silently editing or deleting historical evidence.
