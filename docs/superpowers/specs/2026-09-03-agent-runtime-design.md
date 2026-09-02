# Agent Runtime Foundation Design

**Date:** 2026-09-03  
**Status:** Approved for implementation  
**Scope:** Minimal executable runtime for the Personal Agent OS repository

## Goal

Turn the repository's current runtime contracts into a small, testable, single-process execution engine. A run must discover a registered skill, load and verify its definition, pass the state-machine gates, invoke a skill adapter, validate declared artifacts, and emit an execution trace that proves what happened.

The runtime is domain-agnostic. The TOEFL writing grader remains a skill definition and contract; its grading logic is not implemented as part of this change.

## Current gaps addressed

- `core/workflow.md` is missing even though the repository describes it as a core contract.
- `runtime/state_machine.yaml` references `RECOVERY` without defining its behavior.
- The six components named by `runtime/README.md` do not exist.
- There is no runner, adapter protocol, execution trace writer, or artifact gate.
- The registry version (`1.0.0`) and the TOEFL manifest version (`2.0.0`) disagree.
- The current execution-log schema is too small to represent state transitions, errors, timestamps, and proof status.

## Design decisions

### 1. Runtime shape

Implement a Python 3.11+ package under `runtime/`. It uses `PyYAML` for the repository's YAML contracts and Python standard-library types for the rest of the implementation. The package is invoked from the repository root with `python -m runtime.cli`.

The runtime has no persistent service, database, network dependency, background worker, or parallel scheduler. A run is an isolated process with an explicit output directory.

### 2. Public execution contract

The runner accepts:

- `task`: non-empty human-readable task description;
- `skill`: registry key;
- `input_path`: optional source path, retained in the run context for the adapter;
- `output_dir`: directory where the adapter's declared artifacts and the execution trace are written;
- `executor`: a callable adapter supplied by the caller.

An executor receives a run context and loaded skill metadata. It returns a mapping from each manifest output name to a path relative to `output_dir`. The runner does not infer or fabricate skill output. If the executor does not produce every declared output, the artifact gate fails.

The runner returns a structured result containing the final status, final state, run identifier, trace path, validation messages, and artifact paths. Fatal failures end in `FAILED`; successful runs end in `DELIVER`.

### 3. State machine and gates

The configured happy path is:

`CREATED -> IDENTIFY_TASK -> FIND_SKILL -> LOAD_SKILL -> RUNTIME_CHECK -> EXECUTE -> ARTIFACT -> VALIDATE -> DELIVER`

`RECOVERY` is an explicit non-terminal branch used for recoverable runtime errors. A recovery attempt can return to `RUNTIME_CHECK` once; repeated or non-recoverable errors move to `FAILED`. `FAILED` is a terminal state.

The state manager loads `runtime/state_machine.yaml`, validates all referenced states, and rejects illegal transitions. The runner is the only component allowed to advance state. Each successful or failed transition is recorded in the trace.

Gate behavior:

- `FIND_SKILL`: registry key exists and points inside the repository's `skills/` directory.
- `LOAD_SKILL`: `SKILL.md` and `manifest.yaml` exist, parse successfully, and their name/version agree with the registry entry.
- `RUNTIME_CHECK`: required runtime capabilities named by the manifest are available; output directory is usable; the input path exists when supplied.
- `EXECUTE`: the adapter is invoked and must return declared artifacts without an uncaught exception.
- `ARTIFACT`: every manifest output has a returned path inside `output_dir`, exists, is a regular non-empty file, and is recorded in the trace.
- `VALIDATE`: the trace and artifact contract pass validation; only then is the run deliverable.

### 4. Skill loading and version policy

`registry/skill_registry.yaml` is the discovery index. `manifest.yaml` is the skill's executable contract. The loader requires exact name and version agreement between the two. Version mismatch is a configuration error, not something to silently resolve at runtime.

The initial repository configuration will be aligned to the existing TOEFL manifest at `2.0.0`. Future version changes must update both registry and manifest in one change.

Path resolution is rooted at the repository root and rejects path traversal. Skill metadata is loaded into immutable dataclasses or equivalent read-only structures so adapters cannot mutate the source contract during a run.

### 5. Execution trace and proof

Each run creates one JSON trace at `<output_dir>/execution_trace.json`. It contains:

- a unique `run_id`;
- task, skill, and version;
- UTC start and finish timestamps;
- ordered state transition records;
- ordered execution steps with status and optional error details;
- artifact paths;
- final status and final state;
- proof flags for skill loaded, runtime checked, trace written, artifacts validated, and validation completed.

The trace writer writes atomically through a temporary file in the same directory and then replaces the final trace. The validation engine requires the trace's required fields, a terminal final state, and all proof flags before reporting success. A prose `SKILL.md` is never treated as execution evidence.

### 6. Artifact validation

The artifact manager validates declared outputs by exact manifest name. It resolves adapter-returned paths against `output_dir`, rejects absolute paths and escapes, checks that files are non-empty, and returns normalized paths for the trace. It does not inspect PDF visual quality or domain semantics; those remain skill-specific validators.

### 7. CLI and adapter boundary

The CLI provides a small operational surface:

- `run-demo`: runs a deterministic local adapter against a registered skill to exercise the full state machine and produce a trace plus fixture artifacts;
- `validate-trace`: validates an existing execution trace and its artifact references.

The library runner is the production integration point for a real TOEFL adapter. No fake assessment is presented as a real student result; demo artifacts are explicitly marked as fixtures.

### 8. Failure and recovery policy

Every failure is represented in the trace with a stable error code and human-readable message. Recoverable failures are limited to runtime readiness and output-directory setup. Skill lookup, skill contract, adapter, artifact, and validation failures are terminal after the single recovery attempt. The runner must never report `DELIVER` after a failed gate.

## Proposed repository changes

Create:

- `runtime/__init__.py`
- `runtime/models.py`
- `runtime/registry_loader.py`
- `runtime/skill_loader.py`
- `runtime/state_manager.py`
- `runtime/execution_logger.py`
- `runtime/artifact_manager.py`
- `runtime/validator_engine.py`
- `runtime/runner.py`
- `runtime/cli.py`
- `tests/test_runtime.py`
- `requirements.txt`

Update:

- `core/workflow.md` — canonical workflow and gate contract;
- `runtime/state_machine.yaml` — define recovery and failed states;
- `runtime/execution_log.schema.json` — executable trace schema;
- `runtime/README.md` — setup, CLI, adapter contract, and troubleshooting;
- `registry/skill_registry.yaml` — align TOEFL version to `2.0.0`.

Do not modify the TOEFL `SKILL.md`, templates, schemas, or teacher override policy in this slice.

## Testing strategy

Use Python's built-in `unittest` so the test suite can run without a test framework installation. Tests cover:

1. registry discovery and missing-skill errors;
2. manifest loading, version mismatch, and path traversal rejection;
3. legal and illegal state transitions;
4. successful end-to-end execution with a deterministic fake adapter;
5. missing, empty, and out-of-directory artifacts;
6. adapter exceptions and recovery-to-failed behavior;
7. trace schema/proof validation and CLI trace validation.

The end-to-end fixture writes the six declared TOEFL output names as clearly labeled test artifacts. It verifies that the runtime can complete the contract without claiming that the TOEFL grader itself performed a real assessment.

## Acceptance criteria

- A fresh checkout can install the one declared Python dependency and run the test suite successfully.
- `run-demo` produces a trace whose final state is `DELIVER` and whose proof flags all pass.
- Any missing or invalid gate produces a trace ending in `FAILED` and a non-zero CLI exit code.
- The runtime rejects registry/manifest version drift.
- The runtime never treats a loaded skill definition as proof of execution.
- All declared artifacts are validated before delivery.
- No existing TOEFL skill contract or prior workspace project is changed beyond the registry version alignment described above.

## Alternatives considered

### A. Implement only a CLI script

Rejected because it would make state transitions, logging, and validation difficult to test or reuse from future skills.

### B. Build a long-running service

Rejected for the first vertical slice. It would introduce persistence, process supervision, and deployment concerns before the repository's basic execution contract is executable.

### C. Silently tolerate version mismatches

Rejected because a registry entry and manifest describe different skill contracts. Failing closed preserves execution proof integrity.
