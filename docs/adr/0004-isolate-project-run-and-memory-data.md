---
artifact: adr
version: "1.0"
created: 2026-09-04
status: accepted
---

# ADR-0004: Isolate Project, Run, and Memory Data

## Status

Accepted on 2026-09-04 for all new v0.3+ runs.

## Context

The TOEFL Skill currently contains instance output under its source directory. The repository has no machine-enforced Project, Run, or persistent Memory roots, so source, configuration, student data, artifacts, and reusable knowledge can be confused. Existing output must remain byte-preserved and cannot be deleted during this upgrade.

## Expansion

| Option | Scalability | Complexity | Migration risk | Maintenance cost |
| --- | --- | --- | --- | --- |
| Continue using `skills/*/output/` | Poor across runs and Projects | Low | High privacy and Git risk | High manual cleanup cost |
| Use filesystem `projects/`, project-scoped `runs/`, and scoped `memory/` | Supports multiple local Projects | Medium | Low with copy-and-hash migration | Low for current operating model |
| Add database-backed tenancy and Memory | High | High | High schema, migration, and recovery risk | High operational cost |

## Critique

- Moving existing output instead of copying first risks irreversible data loss.
- A shared run root without Project ids permits cross-Project collisions.
- Automatic promotion lets Memory silently grow and may persist student data.
- A database solves hypothetical concurrency rather than the observed ownership problem.

## Decision

We will store tracked non-sensitive Project configuration under `projects/`, all new instance data under ignored `runs/<project-id>/<run-id>/`, and promoted reusable knowledge under `memory/global/`, `memory/projects/<project-id>/`, or `memory/skills/<skill-id>/`. Runtime may write only `runs/<project-id>/<run-id>/memory/memory_candidate.json`. Persistent promotion is explicit, reviewed, and outside `AgentRuntime.run()`. Existing Skill output will be copied and hash-verified before any separately authorized removal.

## Rejected alternatives

- Permanent `skills/*/output/`: rejected because it mixes code and run data.
- Shared unscoped runs: rejected because it permits collisions and leakage.
- Automatic Memory promotion: rejected because it hides policy and privacy decisions.
- Database-backed storage: rejected because it expands infrastructure without current evidence.

## Consequences

### Positive

- Code, Project configuration, run instances, and reusable Memory have distinct owners.
- New Projects receive isolated run and Memory paths.
- Runtime cannot silently mutate persistent Memory.

### Negative

- Legacy output remains temporarily in its old location and must be classified as legacy.
- Explicit promotion and hash verification add manual review steps.

### Neutral

- The filesystem remains the v0.3+ persistence mechanism.

## Future changes enabled

Storage implementations can later change behind Project, Run, and Memory contracts without moving domain logic into Runtime.

## References

- `docs/policies/MEMORY_POLICY.md`
- `docs/policies/PROJECT_BOUNDARY_POLICY.md`
- `docs/REPOSITORY_STATE.md`
