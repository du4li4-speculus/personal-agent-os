---
artifact: adr
version: "1.0"
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

## Future changes enabled

Alternative Cognition providers can be evaluated behind one lifecycle contract, and richer loops can be proposed through a separate ADR with cost and termination criteria.

## References

- `cognition/README.md`
- `docs/policies/RUNTIME_POLICY.md`
- `docs/policies/MEMORY_POLICY.md`
