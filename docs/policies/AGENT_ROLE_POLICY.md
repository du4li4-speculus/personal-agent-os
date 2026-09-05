# Agent Role Policy v0.3+

## Owner

Agent-role governance owns why an Agent exists and how its bounded responsibility is evaluated. This file is the canonical policy for Agent declarations.

## Owns

Every Agent declaration must define:

- `name`;
- `objective`;
- `responsibility`;
- `inputs`;
- `outputs`;
- `constraints`;
- `evaluation_criteria`;
- `why_agent_required`;
- `why_skill_insufficient`.

## Must not own

- Domain knowledge that belongs in a Skill.
- Core invariants, Cognition protocols, Registry truth, Runtime execution code, or Project configuration.
- Persistent Memory as private Agent state.
- An open-ended mission without measurable output and constraints.

## Invariants

1. Agents are not knowledge containers.
2. An Agent exists only when an independently evaluated role is required and an existing Skill cannot satisfy the responsibility.
3. Evaluation criteria are non-empty, observable, and tied to declared outputs.
4. Inputs and outputs cross boundaries through declared contracts rather than hidden shared state.
5. A new Agent cannot redefine Core, Cognition, Runtime, Registry, Skill, Project, or Memory ownership.

## Enforcement

- The Agent-role schema requires every field and rejects blank rationale or empty evaluation criteria.
- Repository validation checks every declared Agent against the schema.
- Architecture review rejects Agents that embed domain rules or duplicate a Skill.
- Agent creation requires an ADR when it introduces a new orchestration responsibility.

## Change process

Any new Agent type or change to Agent ownership requires Expansion, Critique, and Decision. The decision must answer why the role is necessary, why a Skill is insufficient, how success is evaluated, and how the Agent can be removed or replaced.
