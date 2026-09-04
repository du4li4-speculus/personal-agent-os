# Agent OS Workflow Contract

This document is the human-readable companion to `runtime/state_machine.yaml`. The Runtime is responsible for enforcing this lifecycle and for producing an execution trace for every attempted run.

The canonical Runtime ownership contract is `docs/policies/RUNTIME_POLICY.md`. Memory Candidate and promotion boundaries are canonical in `docs/policies/MEMORY_POLICY.md`. This document describes currently executable behavior; it does not claim that planned Cognition hooks or Registry entrypoints already execute.

## Lifecycle

```text
CREATED
  -> IDENTIFY_TASK
  -> FIND_SKILL
  -> LOAD_SKILL
  -> RUNTIME_CHECK
  -> EXECUTE
  -> ARTIFACT
  -> VALIDATE
  -> DELIVER
```

Any non-terminal state may fail closed to `FAILED`. A recoverable runtime-readiness error may follow this path once:

```text
RUNTIME_CHECK -> RECOVERY -> RUNTIME_CHECK
```

If the retry fails, the run ends at `FAILED`. `DELIVER` and `FAILED` are terminal states.

## State responsibilities and gates

| State | Responsibility | Success gate |
| --- | --- | --- |
| `CREATED` | Create a run context and run id. | Context exists. |
| `IDENTIFY_TASK` | Record the requested task and optional source input. | Task is non-empty. |
| `FIND_SKILL` | Resolve the requested registry key. | Skill is registered, active, and inside `skills/`. |
| `LOAD_SKILL` | Load `SKILL.md` and `manifest.yaml`. | Name, type, version, outputs, and requirements are valid. |
| `RUNTIME_CHECK` | Check runtime capabilities, input, and output directory. | Required capabilities are available and output is writable. |
| `EXECUTE` | Invoke the caller-provided Skill adapter. | Adapter returns an artifact mapping without an exception. |
| `ARTIFACT` | Check adapter output against the manifest. | Every declared output exists, is non-empty, and stays in the output directory. |
| `VALIDATE` | Validate trace structure, proof, and artifact references. | Validation result is valid. |
| `DELIVER` | Mark the run deliverable. | All proof flags are true and the final trace is persisted. |
| `RECOVERY` | Record one recoverable retry. | Retry is available and returns to `RUNTIME_CHECK`. |
| `FAILED` | Record a non-deliverable terminal result. | Failure trace is persisted when the filesystem permits. |

## Execution proof

The Runtime writes `<output-dir>/execution_trace.json`. A successful trace must show:

- a unique run id, task, Skill name, version, timestamps, and final status;
- ordered transitions beginning at `CREATED` and ending at `DELIVER`;
- execution steps and stable error details when relevant;
- the exact artifact paths validated by the artifact gate;
- these proof flags all set to `true`: `skill_loaded`, `runtime_checked`, `execution_traced`, `artifacts_validated`, and `validation_completed`.

Loading a `SKILL.md` is source context only. It is never execution proof.

## Adapter boundary

Library callers provide an adapter with this shape:

```python
def execute(context: RunContext, skill: LoadedSkill) -> Mapping[str, str | Path]:
    ...
```

The returned mapping must contain exactly the output names declared in the Skill manifest. Paths are relative to the run output directory. Domain-specific assessment and PDF/content validation remain inside the Skill adapter or a future Skill validator.

The caller-provided adapter is current pre-v0.3+ behavior. ADR-0003 requires its replacement by a Registry-resolved Skill entrypoint at Task 5; until that commit lands, Registry discovery and execution remain separate operations.

## Version and failure policy

Registry and manifest versions must match exactly. The Runtime does not silently select a version or downgrade a contract. Any mismatch, missing contract, illegal transition, adapter failure, missing artifact, or invalid proof ends in `FAILED`.

## Operational commands

From the repository root, after installing `requirements.txt`:

```bash
python3 -m unittest discover -s tests -v
python3 -m runtime.cli run-demo \
  --skill toefl-writing-grader \
  --output-dir /tmp/personal-agent-os-runtime-demo
python3 -m runtime.cli validate-trace \
  --trace /tmp/personal-agent-os-runtime-demo/execution_trace.json
```

`run-demo` creates labeled fixture artifacts. They are smoke-test outputs and must not be presented as a real TOEFL assessment.

## Governance references

- Runtime policy: `docs/policies/RUNTIME_POLICY.md`
- Memory policy: `docs/policies/MEMORY_POLICY.md`
- Project boundary: `docs/policies/PROJECT_BOUNDARY_POLICY.md`
- Accepted lifecycle decisions: `docs/adr/README.md`
