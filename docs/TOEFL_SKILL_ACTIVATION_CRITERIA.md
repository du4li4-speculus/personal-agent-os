# TOEFL Writing Grader Activation Criteria

## Current status

`toefl-writing-grader` is a `development` Skill. Agent OS Runtime is executable, but the composite TOEFL workflow is not an active executable Skill because it has no registered Skill-local entrypoint and its assessment-to-delivery stages are not implemented behind the Runtime contracts.

Currently implemented and executable in isolation:

- input normalization for text, supported documents, images/screenshots, and Pages packages;
- source identity, hash, role, extraction status, and adapter provenance preservation;
- conservative evidence extraction;
- explicit assessment-readiness gating;
- Skill-owned source-bundle and evidence schema validation.

Currently missing from the composite executable path:

- evidence-grounded assessment execution;
- diagnosis execution;
- learning-loop generation;
- student and parent PDF rendering;
- teacher-dashboard rendering;
- complete domain validation and delivery through a registered TOEFL entrypoint.

The existing rubric, schemas, templates, and historical output are domain specifications or provenance. Their presence does not prove that these missing stages execute.

## Activation rule

Registry status must remain `development` until every gate below passes with current, reproducible evidence. A placeholder entrypoint, copied historical artifact, synthetic success trace, or schema-only fixture cannot satisfy an execution gate.

### 1. Registered entrypoint

- The manifest declares a real Python entrypoint under a Skill-local `src/` package.
- Registry and manifest name, version, status, path, and entrypoint validation pass.
- Production Runtime resolves and invokes the entrypoint through the standard Registry/Skill loader path, without a caller-supplied executor.

### 2. Runtime and domain boundary

- Runtime contains no direct import of TOEFL Skill code and no TOEFL schema fields, rubric bands, scoring rules, diagnosis rules, or report semantics.
- The Skill receives only run-scoped inputs and writes intermediates/artifacts only under the managed run root.
- Input adapters and evidence extraction produce no score, rubric judgment, diagnosis, or learning recommendation.

### 3. Required execution capabilities

- The manifest declares every provider required by the selected implementation, including evidence-grounded assessment and PDF rendering.
- Required providers fail closed before the dependent stage executes.
- Teacher-dashboard rendering is implemented through a declared Skill-local component or typed capability; it cannot be represented by a static template alone.

### 4. Complete domain documents

One end-to-end run produces schema-valid, mutually linked documents for:

- source bundle;
- evidence;
- assessment;
- diagnosis;
- learning loop;
- validation record;
- teacher dashboard.

All schemas remain owned by `skills/toefl-writing-grader/schemas/`. A teacher-dashboard schema must exist and be declared before this gate can pass. Evidence IDs, source IDs, artifact references, and validation references must resolve within the same run.

### 5. Rendered reader artifacts

- Both declared PDFs are generated at their exact manifest paths.
- The student PDF is inspected for required pages, text, score/chart synchronization, and submitted-writing coverage.
- The parent PDF is inspected for its single-page rule and required content.
- Inspection results are recorded in the run-local validation record; file existence alone is insufficient.

### 6. Exact artifact contract

- Every declared intermediate and final output exists at exactly the manifest path.
- No undeclared output is substituted for a missing artifact.
- Runtime structural admission passes before Cognition Critique, and later domain/schema/semantic validation passes before delivery.

### 7. End-to-end proof

- At least one successful trace reaches `DELIVER` through the canonical Runtime lifecycle.
- Failure traces prove missing prompt, unresolved extraction, unavailable required providers, invalid schemas, renderer failure, and validation failure all fail closed at the correct boundary.
- Trace proof distinguishes structural artifact admission from domain validation and deliverability.

### 8. Repository data hygiene

- No student identity, source document, extracted response, generated report, run trace, or Memory Candidate is staged in Git.
- Test fixtures are synthetic, minimal, and contain no student data.
- The historical `831_白雪_试批` output remains unchanged and cannot be used as proof that the current Runtime path executed.

## Activation decision

Activation requires a separate reviewed commit that presents evidence for all eight gates and changes Registry status only after the complete entrypoint and activation contract passes. Until then, documentation and CLI output must continue to describe the Skill as `development`.
