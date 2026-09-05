# Runtime Policy v0.3+

## Owner

The Runtime Control Plane owns generic execution orchestration. This file is the canonical policy for Runtime responsibility.

## Owns

- Lifecycle state transitions and fail-closed terminal behavior.
- Registry lookup and safe Skill entrypoint loading.
- Typed capability gates and run context construction.
- Project-scoped run directories, artifact containment, and execution trace persistence.
- Generic contract and schema invocation, including proof that declared validators ran.
- The existing one-retry policy for recoverable Runtime-readiness failures.

## Must not own

- TOEFL or other domain rules, scoring, diagnosis, report semantics, or domain state names.
- Project goals or Project-specific workflow decisions.
- Cognition protocol content or claims that loading a protocol equals executing it.
- Persistent Memory promotion.
- Arbitrary caller-supplied domain executors on the production path.

## Invariants

1. Runtime source remains domain-neutral and never imports a domain Skill package directly.
2. An active Skill is executed only through the entrypoint resolved from its validated Registry and manifest pair.
3. Required capabilities fail before Skill execution when unavailable.
4. Runtime readiness and its bounded recovery complete before any Cognition provider executes.
5. Structural artifact admission precedes references-based Cognition Critique. Admission proves exact, contained, regular, non-empty outputs normalized into trusted run-relative references; it does not prove domain/schema/semantic correctness, Cognition approval, final Runtime validation, or deliverability.
6. Cognition Critique receives only normalized artifact references and minimum run identity/context, without artifact contents or arbitrary filesystem access.
7. Declared artifacts must pass their later generic/domain validation gates before delivery.
8. Loading, execution, validation, recovery, and failure are represented truthfully in the trace.
9. Runtime writes no persistent Memory.

## Enforcement

- The Runtime state machine rejects illegal transitions and fails closed.
- Registry, Skill, Project, Run, and Memory Candidate documents are schema-validated.
- Entrypoint and artifact paths are resolved under owned roots and reject traversal.
- Architecture tests detect Runtime-to-domain imports and persistent-Memory write targets.
- Runtime and contract tests cover success, failure, recovery, and proof semantics.

## Change process

Any change to lifecycle ownership, execution gates, retries, capability semantics, or data roots requires an Expansion, Critique, and Decision record. The decision must state migration and rollback behavior and prove that no domain rule moved into Runtime.
