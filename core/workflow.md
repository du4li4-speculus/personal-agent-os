# Agent OS Workflow Contract

This document is the human-readable companion to `runtime/state_machine.yaml`. Runtime owns lifecycle enforcement and truthful execution traces; it does not own Skill semantics, Cognition protocol content, Project decisions, or persistent Memory.

This is the canonical v0.3+ lifecycle contract. The tested publication state is recorded in `docs/REPOSITORY_STATE.md`; changes to lifecycle order or state meaning require the ADR process indexed by `docs/adr/README.md`.

## Lifecycle

```text
CREATED
  -> IDENTIFY_TASK
  -> FIND_SKILL
  -> LOAD_SKILL
  -> RUNTIME_CHECK
  -> COGNITION_PREPARE
  -> EXECUTE
  -> ARTIFACT
  -> COGNITION_CRITIQUE
  -> VALIDATE
  -> MEMORY_REVIEW
  -> DELIVER
```

Any non-terminal state may fail closed to `FAILED`. A recoverable Runtime-readiness failure may use the existing one-retry path:

```text
RUNTIME_CHECK -> RECOVERY -> RUNTIME_CHECK
```

Cognition never triggers recovery, automatic self-repair, or Skill re-execution. `DELIVER` and `FAILED` are terminal.

## State responsibilities and gates

| State | Responsibility | Success gate |
| --- | --- | --- |
| `CREATED` | Create the isolated run context and run id. | `runs/<project-id>/<run-id>/` exists. |
| `IDENTIFY_TASK` | Record the task and staged input count. | Task is non-empty. |
| `FIND_SKILL` | Resolve the Project-allowed Registry key. | Skill is registered, active, and contained by `skills/`. |
| `LOAD_SKILL` | Validate the Skill manifest and load its declared entrypoint. | Registry/manifest identity, version, contract, and entrypoint agree. |
| `RUNTIME_CHECK` | Verify run paths, staged inputs, and non-Cognition required capabilities before any Cognition provider executes. | Paths remain under the run and required infrastructure is available; bounded recovery is complete. |
| `COGNITION_PREPARE` | Load selected prepare protocols and optionally request bounded reasoning proposals. | Optional absence is recorded as skipped; required absence fails before Skill execution. |
| `EXECUTE` | Invoke only the Skill-local registered entrypoint. | Entrypoint returns a `SkillExecutionResult`. |
| `ARTIFACT` | Structurally admit declared intermediate and final artifacts. | Outputs are exact, contained, regular, non-empty files normalized into trusted run-relative references. |
| `COGNITION_CRITIQUE` | Request a references-based `pass`, `blocked`, or `review_required` disposition using normalized artifact references and minimum run context. | `pass` continues; the other outcomes fail closed without re-execution. |
| `VALIDATE` | Validate generic execution proof and run-scoped references. | Trace and artifacts satisfy their contracts. |
| `MEMORY_REVIEW` | Optionally propose reusable learning after validation. | No candidate, or one schema-valid run-local proposed Memory Candidate. |
| `DELIVER` | Persist the successful final trace. | Validation completed and no Cognition phase changed run disposition. |
| `RECOVERY` | Record one recoverable Runtime-readiness retry. | Retry returns to `RUNTIME_CHECK`. |
| `FAILED` | Record a non-deliverable result. | Failure trace is persisted when the run filesystem permits. |

## Effective Cognition policy

Skill policy defines whether Cognition is supported or required; Project policy may select stricter execution without redefining Skill semantics.

- Skill `required` always produces effective `required`, including when Project says `disabled`.
- Project `required` escalates Skill `optional` to effective `required`.
- Project `disabled` disables Skill `optional` Cognition.
- Skill `disabled` remains disabled for optional or disabled Projects.
- Project `required` combined with Skill `disabled` is a policy conflict and fails before domain execution.

Missing `cognition.execute` is recorded at `COGNITION_PREPARE`. It fails with `COGNITION_PROVIDER_MISSING` only when effective mode is required; optional mode records an explicit skip. Disabled mode records selected protocol ids without loading or executing them.

## Cognition proof

Each phase trace records:

- selected protocol ids and effective policy;
- whether protocol content was loaded;
- whether a provider actually executed;
- whether the provider response was validated;
- provider outcome and phase status;
- whether that outcome changed run disposition;
- a run-local candidate reference when Memory review creates one.

Loading Markdown is not provider execution and cannot set `executed=true` or `validated=true`. Runtime sends the provider only the protocol content and minimum phase context. It contains no model prompts, vendor behavior, or domain rules.

Prepare responses may contain only advisory framing, expansion, criteria, or decision-support proposals; Runtime does not apply those proposals to immutable contracts or Skill outputs. Critique responses are limited to `pass`, `blocked`, and `review_required`. Memory review may return `no_candidate` or one complete candidate proposal for validation by `MemoryManager`.

## Structural artifact admission

`ARTIFACT` is a structural admission gate, not final validation. It proves that the Skill returned the exact declared outputs, each resolved path remains in its owned run directory, each output is a regular non-empty file, and each persisted reference is normalized relative to the current run.

Passing `ARTIFACT` does not prove domain/schema/semantic correctness, Cognition approval, completion of `VALIDATE`, or deliverability. A later `blocked` or `review_required` Critique leaves the run in `FAILED`; structurally admitted files may remain in the isolated run as evidence but are not deliverable.

The v0.3+ Critique capability receives normalized artifact references plus minimum run identity/context only. Runtime does not provide artifact contents or arbitrary filesystem access. Content-level artifact critique requires a new or superseding ADR and a separately bounded artifact-inspection capability.

## Run and Memory boundaries

External inputs are copied to `input/` before execution. Skills receive run-scoped `work/` and `artifacts/` paths, traces are written to `trace/`, and an optional Memory Candidate is written to `memory/memory_candidate.json` only after validation.

Runtime exposes no persistent promotion API and cannot write `memory/global/`, `memory/projects/`, or `memory/skills/`. Persistent promotion remains a separate reviewed operation.

## Operational commands

From the repository root:

```bash
python3 -m runtime.cli list-skills
python3 -m runtime.cli validate-contracts
python3 -m runtime.cli run \
  --project <project-id> \
  --skill <active-skill> \
  --input <role>=<path>
python3 -m runtime.cli validate-trace \
  --trace runs/<project-id>/<run-id>/trace/execution_trace.json
```

`toefl-writing-grader` remains in `development`; Cognition integration does not activate or complete that domain workflow.

## Governance references

- Runtime policy: `docs/policies/RUNTIME_POLICY.md`
- Memory policy: `docs/policies/MEMORY_POLICY.md`
- Project boundary: `docs/policies/PROJECT_BOUNDARY_POLICY.md`
- Accepted Cognition decision: `docs/adr/0005-integrate-cognition-lifecycle.md`
