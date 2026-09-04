# Extension Policy v0.3+

## Owner

Extension governance owns the admission rules for new Skills, Projects, Agents, Cognition protocols, and capability providers. This file is the canonical policy for architectural extension.

## Owns

- Required evidence and contract gates for adding a new component.
- Rules that prevent a new component from moving responsibility into the wrong layer.
- Compatibility and rollback expectations for extensions.
- The requirement to classify an extension before implementation.

## Must not own

- Domain semantics, Project-specific goals, Runtime implementation details, or persistent Memory records.
- Exceptions that bypass Registry, manifest, validation, or Agent-role contracts.
- Infrastructure introduced only for hypothetical scale.

## Invariants

1. A new Skill can be added without changing Cognition.
2. A new Project can be added without changing Core or global Memory.
3. A new Agent requires a valid role contract, evaluation function, and Skill-insufficiency rationale.
4. A new capability provider does not change Skill domain semantics.
5. An active Skill has a resolvable entrypoint and passing contract tests.
6. Every extension has a reversible commit and preserves existing run data.

## Enforcement

- Registry and manifest validation gates active Skills.
- Project validation gates allowed Skill references and policy values.
- Agent-role validation gates Agent declarations.
- Architecture and repository-hygiene tests prevent backward coupling and tracked run data.
- CI runs contract and boundary tests before integration.

## Change process

Classify the proposed extension, compare minimal/platform/multi-project options, critique hidden coupling and duplicate truth, and record the decision in an ADR. A boundary exception requires explicit repository-owner approval before implementation.
