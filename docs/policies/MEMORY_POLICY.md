# Memory Policy v0.3+

## Owner

The Memory layer owns promoted, reusable knowledge after explicit review. This file is the canonical policy for Memory scope and promotion.

## Owns

- `memory/global/`: stable reusable preferences, reasoning rules, and long-term patterns that apply across Projects and Skills.
- `memory/projects/<project-id>/`: Project architecture decisions, history, and failures.
- `memory/skills/<skill-id>/`: domain edge cases, benchmark failures, and capability improvements.
- Promotion criteria, provenance requirements, and scope selection for reusable knowledge.

## Must not own

- Run inputs, intermediate files, artifacts, or execution traces.
- Unreviewed observations produced during a run.
- Registry status, Skill manifests, Project configuration, or Runtime state.
- Knowledge inferred only from filenames, incomplete evidence, or failed validation.

## Invariants

1. `AgentRuntime.run()` may create only a run-local `memory_candidate` after validation.
2. Runtime cannot write to `memory/global/`, `memory/projects/`, or `memory/skills/`.
3. Persistent Memory promotion is an explicit, reviewable operation outside Runtime execution.
4. Every promoted record identifies its scope, source run, evidence references, reviewer, and promotion decision.
5. Project and Skill records cannot silently become global Memory.
6. Student inputs, reports, and other instance data are not reusable Memory.

## Enforcement

- The Memory Candidate schema accepts only proposed records and rejects a claimed promoted state.
- Run storage confines candidates to `runs/<project-id>/<run-id>/memory/`.
- Architecture tests reject persistent-Memory write targets in Runtime source.
- Promotion tooling, if separately approved, must validate scope and provenance before writing.

## Change process

Any change to Memory ownership, scope, or promotion requires an Expansion, Critique, and Decision record. The ADR must evaluate silent growth, cross-Project leakage, privacy, rollback, and whether the change creates another source of truth.
