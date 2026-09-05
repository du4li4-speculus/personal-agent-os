# Personal Agent OS

Personal Agent OS v0.3+ is an executable, domain-neutral control plane with explicit ownership, execution, and data boundaries. The Runtime is operational; the repository currently has no production-active domain Skill.

## Architecture navigation

The authority and ownership chain is:

`Core -> Cognition -> Runtime Control Plane -> Registry -> Skill -> Project -> Artifacts -> Memory Candidate`

This is an authority flow, not a literal import or call order. Start with [Architecture Boundaries](docs/ARCHITECTURE_BOUNDARIES.md), then use the canonical owners below instead of copying policy text into local implementations:

- [Runtime Policy](docs/policies/RUNTIME_POLICY.md)
- [Memory Policy](docs/policies/MEMORY_POLICY.md)
- [Agent-role Policy](docs/policies/AGENT_ROLE_POLICY.md)
- [Extension Policy](docs/policies/EXTENSION_POLICY.md)
- [Project Boundary Policy](docs/policies/PROJECT_BOUNDARY_POLICY.md)
- [ADR index](docs/adr/README.md)
- [Plan status and precedence](docs/PLAN_STATUS.md)
- [Verified repository state](docs/REPOSITORY_STATE.md)

## Tested current behavior

Runtime can validate machine contracts, resolve an `active` Skill through Registry and its safe Skill-local entrypoint, fail closed on missing required capabilities, stage external inputs into a Project-scoped run, enforce path containment, execute the canonical lifecycle, structurally admit artifacts, validate complete trace transitions, and create at most one run-local proposed Memory Candidate.

The canonical lifecycle is:

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

`ARTIFACT` is structural admission only: declared outputs must be exact, contained, regular, non-empty files represented by normalized run-relative references. It does not prove semantic correctness, Cognition approval, final validation, or deliverability. See [the workflow contract](core/workflow.md) for lifecycle and failure semantics.

Cognition hooks use typed provider boundaries. The trace distinguishes protocol selection/loading from provider execution, skipping, blocking, and validation. Loading a Markdown protocol is not execution proof, and this repository ships no model- or vendor-specific provider implementation.

## Skill readiness

| Registry class | Current Skills | Meaning |
| --- | --- | --- |
| `active` | None | No production domain Skill is currently executable through Registry. Active sample Skills exist only in isolated tests. |
| `development` | `toefl-writing-grader` 2.0.0 | Input normalization, provenance preservation, evidence extraction, readiness gating, and source/evidence schema validation are implemented. |

The TOEFL Skill has no production entrypoint and does not implement assessment execution, diagnosis execution, learning-loop execution, PDF rendering, or dashboard generation. Its complete truth-based activation gates are in [TOEFL Writing Grader Activation Criteria](docs/TOEFL_SKILL_ACTIVATION_CRITERIA.md).

## Data and role locations

| Concern | Location and boundary |
| --- | --- |
| Project configuration | `projects/`; non-sensitive declarative Skill allowlisting and policy only |
| Run instances | `runs/<project-id>/<run-id>/`; staged inputs, work, artifacts, traces, and proposed Memory Candidates |
| Persistent Memory | `memory/global/`, `memory/projects/`, and `memory/skills/`; outside `AgentRuntime.run()` ownership and never updated by candidate creation |
| Agent roles | `agents/`; evaluated orchestration roles that must explain `why_agent_required` and `why_skill_insufficient`, not knowledge containers |

Project configuration cannot redefine Skill semantics, Registry truth, Cognition, Core rules, or domain logic. Persistent Memory promotion is a separate reviewed operation.

## Verified commands

From the repository root with Python 3.11+ and `requirements.txt` installed:

```bash
python3 -m runtime.cli validate-contracts
python3 -m unittest discover -s tests -v
git diff --check
git status --short
```

CI installs dependencies, validates contracts, runs the repository architecture test module and full unit suite, then invokes `git diff --check`. That final command checks whitespace errors only in the diff present in its checkout; it is not an audit of historical repository whitespace.

## Future extension points

Activating a domain Skill, adding content-level Cognition critique, promoting persistent Memory, or completing the TOEFL execution pipeline requires separate work under the existing extension policy and ADR process. These are extension points, not current capabilities.
