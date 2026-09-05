# Agent Core Rules

## Scope

Core defines global principles and system invariants. It does not own domain knowledge, Project decisions, execution implementation, or persistent Memory. Detailed ownership is canonical in `docs/ARCHITECTURE_BOUNDARIES.md` and the policies under `docs/policies/`.

## Execution principles

1. Source before reasoning.
2. Skill before execution.
3. Evidence before assessment.
4. Validation before delivery.
5. Never claim execution without execution proof.

## Cognitive workflow

For non-trivial tasks:

1. Expand the problem space before convergence.
2. Identify evaluation criteria before choosing solutions.
3. Apply critique and assumption testing before implementation.
4. Record only evidence-backed reusable lessons as Memory Candidates.

Cognition protocols guide thinking processes but do not replace domain Skills or Runtime execution.

## Cognition execution boundary

- Selecting or loading a Markdown protocol records context availability only; neither event is proof that Cognition executed.
- Cognition executes only through the typed `cognition.execute` capability and its provider result must pass Runtime validation.
- Prepare-phase results are advisory framing, expansion, criteria, or decision-support proposals. They cannot mutate Project configuration, Skill contracts, Registry truth, Core rules, or domain artifacts.
- Critique may pass, block delivery, or require explicit review. It does not trigger automatic repair or re-execution.
- Memory review occurs only after validation and may create only a run-local proposed Memory Candidate.
- Cognition remains domain-neutral and never owns scores, diagnoses, reports, or Skill outputs.

## Layer usage

- Use Cognition for reusable reasoning, exploration, critique, and decision support.
- Use Skills for domain-specific execution and validation.
- Use Runtime for execution tracking, generic gates, and proof.
- Use Projects for non-sensitive configuration and allowed-Skill selection.
- Use Memory only through its explicit scope and promotion policy.

## Agent role boundary

Agents are bounded, evaluated roles rather than knowledge containers. Every Agent declaration is governed by `docs/policies/AGENT_ROLE_POLICY.md`; domain knowledge remains in Skills, and reusable knowledge remains in scoped Memory.

## Governance references

- Runtime ownership: `docs/policies/RUNTIME_POLICY.md`
- Memory scope and promotion: `docs/policies/MEMORY_POLICY.md`
- Project ownership: `docs/policies/PROJECT_BOUNDARY_POLICY.md`
- Extension admission: `docs/policies/EXTENSION_POLICY.md`
- Architecture decisions: `docs/adr/README.md`

## Priority

Accuracy > speed.
Execution > explanation.
Evidence > assumption.
