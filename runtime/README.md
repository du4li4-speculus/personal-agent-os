# Runtime Layer

Runtime turns workflow rules into executable control. The implementation is a small, single-process Python package with no service or database dependency.

## Components

- `registry_loader` — discovers active Skills and rejects unsafe paths.
- `skill_loader` — loads `SKILL.md` and `manifest.yaml` and enforces exact version agreement.
- `entrypoint_loader` — resolves and invokes the manifest-declared module inside the Skill root.
- `capabilities` — exposes host infrastructure through opaque, typed provider ports.
- `state_manager` — validates and enforces `runtime/state_machine.yaml`.
- `execution_logger` — writes atomic JSON execution traces.
- `artifact_manager` — structurally admits exact, contained, regular, non-empty outputs and normalizes run-relative references.
- `validator_engine` — validates complete state-machine transitions, execution proof, and persisted run references.
- `cognition_manager` — applies typed policy-controlled Cognition hooks without model or domain logic.
- `project_loader` and `run_store` — validate declarative Project selection and isolate run-instance data.
- `memory_manager` — validates at most one run-local proposed Memory Candidate; it has no persistent promotion API.
- `runner` — orchestrates the lifecycle and fail-closed recovery policy.
- `cli` — lists Registry status, validates contracts/traces, and invokes only the managed Runtime path.

Canonical ownership is defined in `docs/ARCHITECTURE_BOUNDARIES.md`; Runtime invariants are defined in `docs/policies/RUNTIME_POLICY.md`.

## Setup

Python 3.11+ is supported. Install the contract dependencies:

```bash
python -m pip install -r requirements.txt
```

## Registered entrypoint contract

The production Runtime accepts only an active Registry entry with a validated manifest entrypoint. Callers provide input references, a run root, and infrastructure capability providers; they cannot inject a domain executor:

```python
from pathlib import Path

from runtime import AgentRuntime, InputRef


result = AgentRuntime(Path.cwd()).run(
    task="Run a Skill task",
    skill_name="an-active-skill",
    project_id="example-project",
    inputs=(InputRef(path=Path("input.txt"), role="source", media_type="text/plain"),),
    run_root=Path("runtime-output"),
    capabilities={},
)
```

The Skill entrypoint receives immutable run and Skill metadata plus a `CapabilitySet`, and returns `SkillExecutionResult`. Required capability ids must be present before execution. Optional providers remain absent unless the Skill's selected execution path requests them. Runtime treats provider identifiers and payloads as opaque infrastructure data and contains no domain rules.

Entrypoint `python_path` values must be relative, must not contain `..`, and must resolve under the Skill root. Imported module files are checked against the same root, temporary module namespaces are removed after execution, and global `sys.path` is restored even when import or execution fails.

## Commands

```bash
python -m runtime.cli list-skills
python -m runtime.cli validate-contracts
python -m unittest discover -s tests -v
python -m runtime.cli validate-trace \
  --trace /path/to/run/execution_trace.json
```

`validate-trace` exits non-zero unless the trace is a complete successful delivery with all proof flags true. The repository's active sample Skill is test-only; `toefl-writing-grader` remains `development` and cannot execute until its complete domain entrypoint is separately approved.

## Proof and failure behavior

The runner writes `execution_trace.json` with the run id, version, state transitions, steps, artifacts, errors, and proof flags. Persisted transitions are checked against the complete canonical state machine. The human-readable lifecycle and Cognition proof contract are maintained in `core/workflow.md`.

`ARTIFACT` proves structural admission only; it does not prove domain/schema/semantic correctness, Cognition approval, final validation, or deliverability. A run reaches `DELIVER` only after the later validation gates pass.

Recoverable output-directory readiness errors can retry once through `RECOVERY`. Contract, entrypoint, capability, artifact, and validation failures end in `FAILED`. Registry and manifest versions must match exactly.

## Data boundary

Runtime stages inputs and writes work files, artifacts, traces, and optional Memory Candidates only under `runs/<project-id>/<run-id>/`. Persistent global, Project, and Skill Memory remain outside `AgentRuntime.run()` ownership. The canonical Project and Memory rules are in `docs/policies/PROJECT_BOUNDARY_POLICY.md` and `docs/policies/MEMORY_POLICY.md`.
