# Project Boundary Policy v0.3+

## Owner

The Project layer owns non-sensitive configuration and policy selection for one bounded objective. This file is the canonical policy for Project responsibility.

## Owns

- Project identity and configuration.
- The allowlist of Skills available to the Project.
- Project-level Cognition mode and Memory policy within upstream constraints.
- Project-local goals, decisions, and references to Project Memory.
- Association of runs with one Project id.

## Must not own

- Core invariants or Cognition protocol definitions.
- Registry identity, version, status, manifest resolution, or entrypoint discovery.
- Skill algorithms, scoring rules, validators, or artifact semantics.
- Runtime lifecycle implementation.
- Global Memory or another Project's Memory and run data.
- Student identity, source paths, or run-instance payloads in tracked Project configuration.

## Invariants

1. A Project selects only registered Skills allowed by its validated manifest.
2. Project configuration cannot weaken a required Skill or Cognition policy.
3. Every run belongs to exactly one Project and remains under `runs/<project-id>/<run-id>/`.
4. Project Memory remains under `memory/projects/<project-id>/` after explicit promotion.
5. Adding a Project requires no change to Core, Cognition, or unrelated Skills.

## Enforcement

- The Project schema restricts allowed fields and values.
- The Project loader validates Skill references and rejects path traversal.
- Run storage validates Project and run identifiers before creating paths.
- Architecture tests reject Project configuration containing run-instance or domain-rule fields.

## Change process

Any expansion of Project authority requires Expansion, Critique, and Decision. The ADR must prove that the responsibility cannot remain in Skill, Runtime, Cognition, or scoped Memory and must identify migration and rollback effects for existing Projects.
