# Runtime Layer

Runtime turns workflow rules into executable control. The implementation is a small, single-process Python package with no service or database dependency.

## Components

- `registry_loader` — discovers active Skills and rejects unsafe paths.
- `skill_loader` — loads `SKILL.md` and `manifest.yaml` and enforces exact version agreement.
- `entrypoint_loader` — resolves and invokes the manifest-declared module inside the Skill root.
- `capabilities` — exposes host infrastructure through opaque, typed provider ports.
- `state_manager` — validates and enforces `runtime/state_machine.yaml`.
- `execution_logger` — writes atomic JSON execution traces.
- `artifact_manager` — validates exact, non-empty, in-directory manifest outputs.
- `validator_engine` — validates execution proof and persisted artifact references.
- `runner` — orchestrates the lifecycle and fail-closed recovery policy.
- `cli` — provides the deterministic demo and trace validation commands.

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
python -m unittest discover -s tests -v
python -m runtime.cli validate-trace \
  --trace /path/to/run/execution_trace.json
```

`validate-trace` exits non-zero unless the trace is a complete successful delivery with all proof flags true. The repository's active sample Skill is test-only; `toefl-writing-grader` remains `development` and cannot execute until its complete domain entrypoint is separately approved.

## Proof and failure behavior

The runner writes `execution_trace.json` with the run id, version, state transitions, steps, artifacts, errors, and proof flags. A run reaches `DELIVER` only after Registry and Skill loading, required-capability checks, registered-entrypoint execution, artifact validation, and trace validation have all completed.

Recoverable output-directory readiness errors can retry once through `RECOVERY`. Contract, entrypoint, capability, artifact, and validation failures end in `FAILED`. Registry and manifest versions must match exactly.
