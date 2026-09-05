---
artifact: adr
version: "1.1"
created: 2026-09-04
status: accepted
---

# ADR-0005: Integrate Cognition Through Explicit Lifecycle Hooks

## Status

Accepted on 2026-09-04 for the v0.3+ lifecycle target.

## Context

Cognition currently exists as reusable Expansion, Critique, Decision, and Memory protocol documents. The Runtime does not execute them, and reading a protocol file is not proof that reasoning occurred. The architecture requires visible `COGNITION_PREPARE`, `COGNITION_CRITIQUE`, and `MEMORY_REVIEW` phases while keeping Cognition free of TOEFL rules and execution code.

## Expansion

| Option | Scalability | Complexity | Migration risk | Maintenance cost |
| --- | --- | --- | --- | --- |
| Load protocol Markdown as context only | Low reuse and no execution proof | Low | High false-claim risk | Medium manual interpretation |
| Add typed optional/required lifecycle hooks | Supports reusable providers and Projects | Medium | Medium, covered by trace tests | Moderate and explicit |
| Create a separate Cognition service | High theoretical reuse | High | High network, state, and proof risk | High operations cost |

## Critique

- Setting `executed=true` after loading Markdown would falsify execution proof.
- Letting a Project weaken a Skill-required Cognition mode violates ownership.
- Automatic re-execution after critique expands lifecycle and cost beyond the approved one-retry Runtime policy.
- A Cognition service creates another trace and policy authority.

## Decision

We will register existing Cognition protocol documents and integrate typed prepare, critique, and Memory-review hooks. Trace will distinguish loaded, executed, skipped, blocked, and validated. Optional hooks without a provider are recorded as skipped; required hooks fail closed. A blocked or review-required critique ends the run without an automatic re-execution loop. Memory review may create only a run-local candidate after validation.

## Rejected alternatives

- Treat loading as execution: rejected because it creates false proof.
- Embed Cognition rules in each Skill: rejected because it prevents reuse and duplicates reasoning policy.
- Automatic critique/retry loop: rejected because it changes the approved lifecycle and cost boundary.
- Separate service: rejected because v0.3+ needs contracts before distributed infrastructure.

## Consequences

### Positive

- Cognition becomes reusable and observable without entering domain code.
- Required and optional reasoning policies have explicit failure semantics.
- Memory review cannot bypass validation.

### Negative

- Trace and state-machine contracts become larger.
- Useful execution requires a typed Cognition provider; documents alone remain non-executable.

### Neutral

- Existing protocol Markdown remains unchanged and is registered rather than rewritten.

## Amendment: Lifecycle Ordering Reconciliation

Accepted on 2026-09-05 after the Task 7 implementation review. This amendment preserves the original decision above and records the approved ordering clarification rather than rewriting its history.

### Expansion

Two lifecycle orderings were evaluated:

1. Restore `LOAD_SKILL -> COGNITION_PREPARE -> RUNTIME_CHECK -> EXECUTE -> COGNITION_CRITIQUE -> ARTIFACT`.
2. Retain `LOAD_SKILL -> RUNTIME_CHECK -> COGNITION_PREPARE -> EXECUTE -> ARTIFACT -> COGNITION_CRITIQUE`.

Restoring the earlier target would preserve its diagram literally, but it would execute Cognition before Runtime readiness and require Critique to consume either unsafe raw outputs or a new provisional artifact-view contract. Retaining the implemented order allows readiness and bounded recovery to complete before provider execution, and gives Critique only normalized references that have passed structural admission.

### Critique

- Earlier Cognition execution can spend provider capacity and expose context for a run that cannot pass basic readiness.
- Critique before structural admission can encounter missing, empty, absolute, traversing, or escaped output paths unless another admission boundary is introduced.
- Structural admission before Critique can be misread as final validation unless its proof boundary is explicit.
- A references-only Critique cannot assess artifact contents. Adding content access would expand the capability, data-exposure, and proof contracts beyond v0.3+.

### Decision

The canonical v0.3+ lifecycle is:

```text
LOAD_SKILL
-> RUNTIME_CHECK
-> COGNITION_PREPARE
-> EXECUTE
-> ARTIFACT
-> COGNITION_CRITIQUE
-> VALIDATE
-> MEMORY_REVIEW
-> DELIVER
```

`RUNTIME_CHECK` precedes Cognition provider execution for fail-fast behavior, recovery isolation, cost control, and minimum unnecessary data exposure. Required Cognition still fails closed in `COGNITION_PREPARE` before Skill execution.

`ARTIFACT` is structural artifact admission only. It proves exact declared outputs, containment, regular non-empty files, and normalization into trusted run-relative references. It does not prove domain/schema/semantic correctness, Cognition approval, final Runtime validation, or deliverability.

The v0.3+ `COGNITION_CRITIQUE` phase receives only normalized artifact references and minimum run identity/context. It receives neither artifact contents nor arbitrary filesystem access. Content-level artifact critique requires a new or superseding ADR and a bounded artifact-inspection capability that defines allowed access, size limits, media handling, sensitive-data exposure, and trace/proof semantics.

### Consequences

- Runtime-readiness failure and recovery occur before any Cognition provider call, so recovery does not repeat Prepare.
- Artifact-admission failure prevents Critique from executing.
- A blocked or review-required Critique may follow successful structural admission, but the run and its artifacts remain non-deliverable.
- Persisted traces must validate every transition against the canonical state machine and cannot claim the superseded lifecycle order.

## Future changes enabled

Alternative Cognition providers can be evaluated behind one lifecycle contract, and richer loops can be proposed through a separate ADR with cost and termination criteria.

## References

- `cognition/README.md`
- `docs/policies/RUNTIME_POLICY.md`
- `docs/policies/MEMORY_POLICY.md`
