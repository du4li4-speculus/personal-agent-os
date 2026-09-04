---
artifact: adr
version: "1.0"
created: 2026-09-04
status: accepted
---

# ADR-0002: Enforce One-Way Layer Ownership

## Status

Accepted on 2026-09-04 as the governing layer model for Agent OS v0.3+.

## Context

The repository has Core, Cognition, Runtime, Registry, Skill, Project, Artifact, and Memory concerns, but earlier documents describe them with overlapping language. Without one authority chain, Core and Cognition can both appear to own reasoning, Projects can redefine Skill behavior, and Runtime can absorb domain rules. The architecture directive requires:

`Core -> Cognition -> Runtime Control Plane -> Registry -> Skill -> Project -> Artifacts -> Memory Candidate`

## Expansion

| Option | Scalability | Complexity | Migration risk | Maintenance cost |
| --- | --- | --- | --- | --- |
| Preserve informal directory boundaries | Poor; each extension reinterprets ownership | Low initially | High hidden-coupling risk | High review cost |
| Adopt one authority chain plus enforceable policies | Supports additional Skills and Projects | Medium | Low; documents precede code changes | Moderate, bounded by tests |
| Split layers into independent services | High theoretical scale | Very high | High operational and data migration risk | High service ownership cost |

## Critique

- Treating the chain as a Python import graph is incorrect: Runtime must read downstream Registry and Skill descriptors to orchestrate execution.
- Treating dynamic entrypoint loading as permission for domain imports would move Skill knowledge into Runtime.
- Repeating full normative rules in Core, README, policy, and Project files would create competing sources of truth.

## Decision

We will use the required chain as the one-way ownership and execution-authority flow. An upstream layer defines constraints that downstream layers cannot redefine. Source-code dependencies are evaluated separately: Runtime may resolve validated Registry and Skill descriptors and invoke a declared entrypoint through generic interfaces, but Runtime source cannot import domain Skill modules directly. Canonical policies own detailed rules; Core and README files link to them and summarize current behavior.

## Rejected alternatives

- Informal directory-only boundaries: rejected because they are not testable.
- Literal import direction matching every arrow: rejected because it prevents Runtime from discovering and invoking Skills.
- Service-per-layer architecture: rejected because no current scale or isolation evidence justifies network and operational complexity.
- Multiple normative copies of each rule: rejected because they drift.

## Consequences

### Positive

- Ownership conflicts have one resolution path.
- Runtime can remain domain-neutral while still executing Skills.
- New Skills and Projects can be evaluated against stable boundaries.

### Negative

- Reviews must distinguish authority flow, configuration references, and code imports.
- Boundary tests and ADR maintenance add deliberate process overhead.

### Neutral

- The v0.3+ Runtime remains a single-process Python system.

## Future changes enabled

Layers can later move behind processes or services without changing their ownership contracts, provided a new ADR records the changed integration boundary.

## References

- `docs/AGENT_OS_ARCHITECTURE_EVOLUTION_v0.3_PLUS.md`
- `docs/ARCHITECTURE_BOUNDARIES.md`
- `docs/policies/EXTENSION_POLICY.md`
