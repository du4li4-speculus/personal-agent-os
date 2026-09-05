---
artifact: adr
version: "1.0"
created: 2026-09-04
status: accepted
---

# ADR-0003: Resolve Skills Through Registry Entrypoints

## Status

Accepted on 2026-09-04 for the v0.3+ execution contract.

## Context

The current Runtime validates Registry and Skill metadata but requires the caller to provide an arbitrary executor callable. That path allows execution knowledge to bypass Registry discovery. The current GitHub Registry/manifest pair also contains a version mismatch, and the TOEFL Skill does not yet expose a complete production entrypoint.

## Expansion

| Option | Scalability | Complexity | Migration risk | Maintenance cost |
| --- | --- | --- | --- | --- |
| Retain caller-supplied executors | Poor; every caller needs domain wiring | Low | High contract-bypass risk | High duplicated integration code |
| Resolve a safe local entrypoint from validated Registry and manifest data | Supports new local Skills | Medium | Medium, controlled by fixture tests | Low central discovery cost |
| Introduce a remote plugin broker | Supports distributed capabilities | High | High trust, network, and compatibility risk | High operational cost |

## Critique

- Caller injection makes Registry descriptive rather than authoritative.
- Marking a Skill active without an entrypoint creates false capability claims.
- Importing a known TOEFL module in Runtime would solve one case by violating the domain boundary.
- A remote broker adds infrastructure before local contracts are stable.

## Decision

We will require every active Registry entry to match a versioned Skill manifest and expose a safe, resolvable local entrypoint. Runtime will load it through a generic entrypoint interface, enforce path containment, and provide external tools through typed capabilities. Development Skills may omit an entrypoint but cannot be advertised as active. The production `AgentRuntime.run()` path will not accept an arbitrary caller executor.

## Rejected alternatives

- Keep executor injection: rejected because it bypasses Registry truth.
- Hard-code Skill imports in Runtime: rejected because it creates domain coupling.
- Add a fake TOEFL entrypoint: rejected because it would claim an incomplete assessment-to-report pipeline.
- Remote plugin broker: rejected because it adds network and trust scope not required by v0.3+.

## Consequences

### Positive

- Registry becomes the machine-verifiable discovery authority.
- A new active Skill can be added without modifying Runtime.
- Capability failures can occur before domain execution.

### Negative

- Existing tests using executor injection must migrate to fixture Skills.
- Dynamic loading requires strict path and module-origin validation.

### Neutral

- TOEFL remains `development` until its complete entrypoint contract passes.

## Future changes enabled

Additional local Skills and capability providers can be introduced under one execution contract; a remote broker can be reconsidered only with evidence and a new ADR.

## References

- `docs/REGISTRY_POLICY.md`
- `docs/policies/RUNTIME_POLICY.md`
- `docs/TOEFL_SKILL_ACTIVATION_CRITERIA.md` when created by the approved plan
