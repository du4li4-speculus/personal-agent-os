# Runtime Layer

Runtime turns workflow rules into executable control. The implementation is a small, single-process Python package with no service or database dependency.

## Components

- `registry_loader` — discovers active Skills and rejects unsafe paths.
- `skill_loader` — loads `SKILL.md` and `manifest.yaml` and enforces exact version agreement.
- `state_manager` — validates and enforces `runtime/state_machine.yaml`.
- `execution_logger` — writes atomic JSON execution traces.
- `artifact_manager` — validates exact, non-empty, in-directory manifest outputs.
- `validator_engine` — validates execution proof and persisted artifact references.
- `runner` — orchestrates the lifecycle and fail-closed recovery policy.
- `cli` — provides the deterministic demo and trace validation commands.

## Setup

Python 3.11+ is supported. Install the YAML dependency:

```bash
python -m pip install -r requirements.txt
```

## Library adapter contract

The runtime is domain-agnostic. A real Skill integration supplies an adapter:

```python
from pathlib import Path
from typing import Mapping

from runtime import AgentRuntime
from runtime.models import LoadedSkill, RunContext


def execute(context: RunContext, skill: LoadedSkill) -> Mapping[str, str | Path]:
    # Produce exactly the output names in skill.outputs.
    ...


result = AgentRuntime(Path.cwd()).run(
    task="Run a Skill task",
    skill_name="toefl-writing-grader",
    executor=execute,
    output_dir=Path("runtime-output"),
)
```

The adapter receives immutable Skill metadata and returns paths relative to the run output directory. It must not claim domain assessment success unless the Skill itself performed that work.

## Commands

```bash
python -m unittest discover -s tests -v
python -m runtime.cli run-demo \
  --skill toefl-writing-grader \
  --output-dir /tmp/personal-agent-os-runtime-demo
python -m runtime.cli validate-trace \
  --trace /tmp/personal-agent-os-runtime-demo/execution_trace.json
```

`run-demo` writes explicitly labeled fixture artifacts for the full state-machine smoke test. It does not perform TOEFL grading. `validate-trace` exits non-zero unless the trace is a complete successful delivery with all proof flags true.

## Proof and failure behavior

The runner writes `execution_trace.json` with the run id, version, state transitions, steps, artifacts, errors, and proof flags. A run reaches `DELIVER` only after Skill loading, runtime checks, adapter execution, artifact validation, and trace validation have all completed.

Recoverable output-directory readiness errors can retry once through `RECOVERY`. Contract, adapter, artifact, and validation failures end in `FAILED`. Registry and manifest versions must match exactly.
