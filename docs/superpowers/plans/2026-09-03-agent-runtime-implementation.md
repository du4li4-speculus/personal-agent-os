# Agent Runtime Foundation Implementation Plan

> **Execution note:** Implement this plan task-by-task in the repository root. Each task ends with a focused test or inspection before moving on.

## Objective

Implement the approved runtime design from `docs/superpowers/specs/2026-09-03-agent-runtime-design.md`: a single-process Python runtime that discovers a registered skill, loads and verifies its manifest, enforces the configured state machine, records execution proof, validates artifacts, and exposes a deterministic demo CLI.

## Constraints and non-goals

- Keep the runtime domain-agnostic; do not implement TOEFL grading logic in this change.
- Do not modify the TOEFL `SKILL.md`, templates, schemas, or teacher override policy.
- Do not add a service, database, network client, worker queue, or persistent memory layer.
- Use Python 3.11+ and `PyYAML`; use `unittest` for tests.
- Keep all paths rooted at the repository root and reject traversal outside the declared output directory.
- Preserve execution-proof semantics: a loaded Skill definition is not evidence that execution occurred.

## Task 1: Establish package and dependency baseline

Files:

- Create `runtime/__init__.py`.
- Create `requirements.txt` with the pinned-compatible `PyYAML` dependency.

Implementation:

- Export the public runtime types only from `runtime/__init__.py` after they exist.
- Keep the package importable from the repository root with `python -c "import runtime"`.

Verification:

- Install or confirm the dependency in the active Python environment.
- Run the import smoke test.

## Task 2: Add immutable runtime data models

Files:

- Create `runtime/models.py`.

Implementation:

- Define immutable models for registry entries, loaded skill metadata, run context, state transitions, execution steps, proof flags, and run results.
- Keep serialization explicit so traces contain plain JSON-compatible values.
- Represent paths as resolved `Path` values internally and normalized strings in trace output.
- Add stable error fields (`code`, `message`, optional `recoverable`) to step/result models.

Tests first in `tests/test_runtime.py`:

- Construct a context and confirm required fields are present.
- Confirm the result serializer produces JSON-compatible data.

Verification:

- Run the focused model tests before proceeding.

## Task 3: Implement registry discovery

Files:

- Create `runtime/registry_loader.py`.
- Update `registry/skill_registry.yaml` so `toefl-writing-grader` is `2.0.0`, matching its manifest.

Implementation:

- Load `registry/skill_registry.yaml` with `yaml.safe_load`.
- Validate the top-level `skills` mapping and each entry's required `version`, `type`, `status`, and `path` fields.
- Expose `get(skill_name)` and a list method for diagnostics.
- Resolve each skill path under the repository's `skills/` directory and reject absolute paths, traversal, missing directories, and unsupported status values.
- Raise typed, stable errors for malformed registry data and missing skill keys.

Tests first:

- Discover the existing TOEFL skill.
- Reject an unknown skill.
- Reject a traversal path and malformed registry fixture.

Verification:

- Run registry tests and inspect the registry diff to ensure only the intended version changes.

## Task 4: Implement Skill contract loading

Files:

- Create `runtime/skill_loader.py`.

Implementation:

- Load the registry entry, `SKILL.md`, and `manifest.yaml` into a `LoadedSkill` model.
- Require the Skill directory and both contract files to exist and be regular files.
- Validate manifest name/version against the registry entry exactly.
- Validate manifest `outputs` and `requires` as lists of strings.
- Preserve the Skill definition text as source context but never use its presence as execution proof.
- Make the loader reject manifest path escapes and version drift with typed errors.

Tests first:

- Load the existing TOEFL manifest successfully.
- Create a temporary mismatch fixture and assert a version error.
- Assert missing `SKILL.md`/`manifest.yaml` errors.

Verification:

- Run loader tests and confirm all source files remain untouched except the registry alignment.

## Task 5: Complete and enforce the state machine

Files:

- Update `runtime/state_machine.yaml`.
- Create `runtime/state_manager.py`.

Implementation:

- Define `RECOVERY` and terminal `FAILED` in the YAML contract.
- Load and validate all states and referenced next states before a run starts.
- Expose the current state and `can_transition(next_state)`.
- Reject illegal transitions, transitions out of terminal states, and malformed state definitions.
- Track one recovery attempt per run; allow `RECOVERY -> RUNTIME_CHECK` only for the recoverable runtime checks described in the design.
- Keep state manager side-effect-free apart from its in-memory current state.

Tests first:

- Walk the complete happy path.
- Reject a skipped state and a transition out of `DELIVER`/`FAILED`.
- Verify one recovery retry is allowed and a second attempt is terminal.

Verification:

- Run state tests and validate every `next` reference in the YAML.

## Task 6: Implement trace logging and atomic persistence

Files:

- Create `runtime/execution_logger.py`.
- Update `runtime/execution_log.schema.json`.

Implementation:

- Create a trace at run start with UTC ISO-8601 timestamps and a UUID run id.
- Record state transitions and execution steps in order, including success/failure and stable error codes.
- Track proof flags: `skill_loaded`, `runtime_checked`, `execution_traced`, `artifacts_validated`, and `validation_completed`.
- Persist to `<output_dir>/execution_trace.json` using a same-directory temporary file followed by atomic replacement.
- Keep updates deterministic and JSON serializable.

Tests first:

- Assert trace contents after a successful state transition.
- Assert failed steps retain error code and message.
- Assert the trace file is created and can be loaded back.

Verification:

- Run trace tests and validate the sample trace against the updated schema using the runtime validator.

## Task 7: Implement artifact management

Files:

- Create `runtime/artifact_manager.py`.

Implementation:

- Accept manifest output names and the adapter's returned name-to-path mapping.
- Require every declared output exactly once; reject undeclared outputs.
- Resolve paths against `output_dir`, reject absolute paths and path escapes, and require regular non-empty files.
- Return normalized artifact records for the trace.
- Keep domain-specific PDF/content validation outside this component.

Tests first:

- Accept all declared fixture outputs.
- Reject a missing output, empty file, directory, absolute path, and `../` escape.
- Reject an extra undeclared output.

Verification:

- Run artifact tests and verify no file outside the temporary output directory is touched.

## Task 8: Implement trace and artifact validation

Files:

- Create `runtime/validator_engine.py`.

Implementation:

- Validate required trace fields, statuses, terminal final state, ordered state records, and proof flags.
- Validate artifact paths still exist and remain inside the output directory.
- Return structured validation results rather than throwing for expected validation failures.
- Require all proof flags before declaring a run deliverable.
- Make schema validation compatible with the repository's JSON schema contract without introducing a second schema engine dependency.

Tests first:

- Accept a complete proof-bearing trace.
- Reject a trace with missing proof, non-terminal state, missing artifact, or inconsistent final status.

Verification:

- Run validator tests against both in-memory traces and the persisted JSON trace.

## Task 9: Implement the runner and recovery policy

Files:

- Create `runtime/runner.py`.

Implementation:

- Orchestrate the exact sequence `CREATED` through `DELIVER`.
- Validate task and input prerequisites at `IDENTIFY_TASK`/`RUNTIME_CHECK`.
- Discover and load the Skill through the loaders; set proof flags only after each gate succeeds.
- Check runtime requirements and prepare the output directory.
- Invoke the supplied executor with immutable run context and loaded Skill metadata.
- Pass executor output to the artifact manager and validator.
- On recoverable runtime failure, enter `RECOVERY`, record the failure, retry once, then fail closed.
- On any fatal failure, record it, transition to `FAILED`, persist the trace, and return a non-deliverable result.
- Ensure no exception path claims `DELIVER` and no successful result is returned before the final trace is persisted.

Tests first:

- Successful end-to-end run with a deterministic fake executor.
- Adapter exception produces `FAILED` and a non-zero outcome.
- Missing artifact produces `FAILED`.
- Runtime readiness failure exercises `RECOVERY` and then `FAILED` after retry.
- Confirm the trace proves the exact executed states.

Verification:

- Run the complete Python test suite.

## Task 10: Add CLI and documentation

Files:

- Create `runtime/cli.py`.
- Update `core/workflow.md`.
- Update `runtime/README.md`.

Implementation:

- Add `run-demo --skill --output-dir` for a clearly labeled deterministic fixture adapter.
- Add `validate-trace --trace` for validating a persisted trace and referenced artifacts.
- Use non-zero exit codes for failed runs or invalid traces.
- Document installation, library adapter contract, state transitions, output layout, proof semantics, and troubleshooting.
- Make the workflow document the human-readable companion to `runtime/state_machine.yaml`, including gates and failure behavior.

Tests first:

- Invoke the CLI through `unittest`/subprocess against a temporary output directory.
- Assert `run-demo` produces `DELIVER` and `validate-trace` returns success.
- Assert an intentionally corrupted trace returns failure.

Verification:

- Run the documented commands from a clean repository root.

## Task 11: Full validation and handoff

Checks:

1. Install dependencies from `requirements.txt` if needed.
2. Run `python -m unittest discover -s tests -v`.
3. Run `python -m runtime.cli run-demo --skill toefl-writing-grader --output-dir <temporary-dir>`.
4. Run `python -m runtime.cli validate-trace --trace <temporary-dir>/execution_trace.json`.
5. Run `git diff --check`.
6. Inspect `git status` and confirm only planned files changed.

Deliverables:

- Executable runtime package and CLI.
- Completed workflow/state-machine contracts.
- Trace and artifact validation.
- Unit/integration tests.
- Updated runtime documentation.

## Suggested commit sequence

1. `feat: add runtime contracts and loaders`
2. `feat: enforce runtime states and execution proof`
3. `feat: add runtime runner and CLI`
4. `test: cover runtime execution and failure paths`
5. `docs: document runtime operation`

Squashing is optional; keep commits separated if review benefits from the boundaries.
