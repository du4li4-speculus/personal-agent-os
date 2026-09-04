---
artifact: adr
version: "1.0"
created: 2026-09-04
status: accepted
---

# ADR-0006: Govern Agents as Evaluated Roles

## Status

Accepted on 2026-09-04 for all new Agent declarations.

## Context

An unconstrained Agent can become a second location for domain knowledge, policy, hidden state, or duplicated Skill logic. The architecture directive states that Agents are not knowledge containers and requires every Agent to define its objective, responsibility, interfaces, constraints, and evaluation function. The repository currently has no machine-verifiable Agent-role contract.

## Expansion

| Option | Scalability | Complexity | Migration risk | Maintenance cost |
| --- | --- | --- | --- | --- |
| Continue with free-form Agent prompts | Poor governance as roles grow | Low | High hidden-ownership risk | High review ambiguity |
| Add a policy and machine-verifiable role contract | Supports bounded specialized roles | Medium | Low because no existing Agent instances migrate | Low, enforced centrally |
| Add an autonomous Agent registry/service | High theoretical orchestration | High | High lifecycle and authority risk | High operations and evaluation cost |

## Critique

- A persona or long prompt is not an ownership contract.
- An Agent without evaluation criteria cannot be accepted or retired objectively.
- If an existing Skill can perform the work, a new Agent duplicates capability and adds orchestration state.
- Private Agent Memory would bypass global, Project, and Skill Memory governance.

## Decision

We will require every Agent declaration to provide `name`, `objective`, `responsibility`, `inputs`, `outputs`, `constraints`, `evaluation_criteria`, `why_agent_required`, and `why_skill_insufficient`. Agents may coordinate bounded work but cannot store domain knowledge, redefine layer policy, or own persistent Memory. A new orchestration responsibility requires a new or amended ADR.

## Rejected alternatives

- Free-form prompts: rejected because ownership and evaluation remain implicit.
- Persona-only declarations: rejected because personality does not define responsibility or acceptance criteria.
- Agent-specific domain knowledge stores: rejected because Skills and scoped Memory already own those concerns.
- Autonomous Agent service: rejected because no current requirement justifies a new control plane.

## Consequences

### Positive

- Agent creation has a measurable purpose and review gate.
- Domain knowledge remains in Skills and scoped Memory.
- Redundant Agents can be rejected before implementation.

### Negative

- Agent proposals require additional rationale and evaluation design.
- Some broad assistants must be decomposed into Skills or smaller roles.

### Neutral

- This decision defines contracts but does not create an Agent instance.

## Future changes enabled

Specialized Agents can be introduced without becoming hidden capability or knowledge containers, and their effectiveness can be evaluated consistently.

## References

- `docs/policies/AGENT_ROLE_POLICY.md`
- `docs/policies/EXTENSION_POLICY.md`
- `core/agent.md`
