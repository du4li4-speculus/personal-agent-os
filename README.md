# Personal Agent OS

A reusable, executable AI workflow operating system with explicit Runtime, Skill, Project, Cognition, artifact, and Memory boundaries.

## Current execution status

- Agent OS Runtime is executable. It resolves active Skills through the Registry, runs them inside Project-scoped run directories, records lifecycle proof, admits structurally valid artifacts, and validates run traces.
- `toefl-writing-grader` remains `development` and is not selectable through the production Runtime path.
- The currently executable TOEFL code is limited to input normalization, provenance preservation, evidence extraction, assessment-readiness gating, and source/evidence schema validation.
- TOEFL assessment, diagnosis, learning-loop execution, PDF rendering, teacher-dashboard rendering, and the composite Skill entrypoint are not implemented.

See [TOEFL Writing Grader Activation Criteria](docs/TOEFL_SKILL_ACTIVATION_CRITERIA.md) for the gates that must all pass before the Registry may mark the Skill active.

## Architecture

- `core/`: global rules and workflow contract
- `cognition/`: reusable reasoning protocols
- `runtime/`: domain-neutral execution and validation control plane
- `registry/`: Skill identity, version, status, and discovery truth
- `skills/`: domain-owned contracts and implementations
- `projects/`: non-sensitive declarative Skill selection and policy
- `runs/`: ignored Project/run instance data
- `memory/`: explicitly reviewed persistent knowledge outside Runtime ownership

## Execution principle

Source -> Skill -> Runtime -> Execution Proof -> Artifact -> Validation
