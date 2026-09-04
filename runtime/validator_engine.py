"""Validate execution proof and run-scoped persisted references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .artifact_manager import ArtifactManager
from .models import ArtifactValidationError, ValidationResult


REQUIRED_TRACE_FIELDS = {
    "run_id",
    "project_id",
    "task",
    "skill",
    "version",
    "input_refs",
    "run_record",
    "started_at",
    "finished_at",
    "transitions",
    "steps",
    "artifacts",
    "proof",
    "status",
    "final_state",
}
REQUIRED_RUN_RECORD_FIELDS = {
    "schema_version",
    "run_id",
    "project_id",
    "skill_name",
    "skill_version",
    "state",
    "input_refs",
    "artifact_refs",
    "trace_ref",
}
REQUIRED_PROOF_FLAGS = {
    "skill_loaded",
    "runtime_checked",
    "execution_traced",
    "artifacts_validated",
    "validation_completed",
}


class ValidatorEngine:
    """Return structured validation results for a completed trace."""

    def validate_trace_file(self, trace_path: Path) -> ValidationResult:
        resolved_trace = Path(trace_path).resolve()
        try:
            with resolved_trace.open("r", encoding="utf-8") as handle:
                trace = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return ValidationResult(False, (f"Unable to read trace: {exc}",))
        run_root = (
            resolved_trace.parent.parent
            if resolved_trace.parent.name == "trace"
            else resolved_trace.parent
        )
        return self.validate_trace(trace, run_root=run_root)

    def validate_trace(
        self,
        trace: Mapping[str, Any],
        *,
        run_root: Path | None = None,
        output_dir: Path | None = None,
        require_deliverable: bool = True,
    ) -> ValidationResult:
        """Validate trace shape, proof, and references inside one run.

        ``output_dir`` remains a compatibility input for standalone callers. New
        Runtime code supplies ``run_root`` so all references share one boundary.
        """

        errors: list[str] = []
        missing = sorted(REQUIRED_TRACE_FIELDS - set(trace.keys()))
        if missing:
            errors.append(f"Missing trace fields: {', '.join(missing)}")
            return ValidationResult(False, tuple(errors))

        for field in (
            "run_id",
            "project_id",
            "task",
            "skill",
            "version",
            "started_at",
        ):
            if not isinstance(trace[field], str) or not trace[field].strip():
                errors.append(f"Trace field must be a non-empty string: {field}")
        if require_deliverable:
            if trace["status"] != "SUCCEEDED":
                errors.append(f"Trace is not successful: {trace['status']}")
            if trace["final_state"] != "DELIVER":
                errors.append(f"Trace did not reach DELIVER: {trace['final_state']}")
            if not isinstance(trace["finished_at"], str) or not trace[
                "finished_at"
            ].strip():
                errors.append("A deliverable trace must have finished_at")
        elif trace["status"] not in {"RUNNING", "SUCCEEDED"}:
            errors.append(f"In-progress trace has invalid status: {trace['status']}")
        if not isinstance(trace["steps"], list) or not trace["steps"]:
            errors.append("Trace steps must be a non-empty list")
        if not isinstance(trace["transitions"], list) or not trace["transitions"]:
            errors.append("Trace transitions must be a non-empty list")
        if not isinstance(trace["artifacts"], dict):
            errors.append("Trace artifacts must be a mapping")
        elif any(not isinstance(value, str) for value in trace["artifacts"].values()):
            errors.append("Trace artifact references must be strings")
        if not isinstance(trace["input_refs"], list):
            errors.append("Trace input_refs must be a list")
        if not isinstance(trace["proof"], dict):
            errors.append("Trace proof must be a mapping")
        else:
            missing_proof = sorted(REQUIRED_PROOF_FLAGS - set(trace["proof"].keys()))
            if missing_proof:
                errors.append(f"Missing proof flags: {', '.join(missing_proof)}")
            if require_deliverable:
                for flag in REQUIRED_PROOF_FLAGS:
                    if trace["proof"].get(flag) is not True:
                        errors.append(f"Proof flag is not true: {flag}")

        if isinstance(trace.get("transitions"), list) and trace["transitions"]:
            first = trace["transitions"][0]
            last = trace["transitions"][-1]
            if not isinstance(first, dict) or first.get("to") != "CREATED":
                errors.append("Trace must begin at CREATED")
            expected_last_state = "DELIVER" if require_deliverable else trace["final_state"]
            if not isinstance(last, dict) or last.get("to") != expected_last_state:
                errors.append(f"Trace must end at {expected_last_state}")
            for transition in trace["transitions"]:
                if not isinstance(transition, dict) or not transition.get("to"):
                    errors.append("Trace contains an invalid state transition")

        self._validate_run_record(trace, errors)

        resolved_run_root: Path | None = None
        artifact_dir: Path | None = None
        if run_root is not None:
            resolved_run_root = Path(run_root).resolve()
            artifact_dir = resolved_run_root / "artifacts"
            if resolved_run_root.name != trace.get("run_id"):
                errors.append("Run root does not match trace run_id")
            if resolved_run_root.parent.name != trace.get("project_id"):
                errors.append("Run root does not match trace project_id")
            self._validate_run_refs(trace, resolved_run_root, errors)
        elif output_dir is not None:
            artifact_dir = Path(output_dir).resolve()

        if artifact_dir is not None and isinstance(trace.get("artifacts"), dict):
            try:
                artifact_errors = ArtifactManager(
                    artifact_dir, run_root=resolved_run_root or artifact_dir
                ).validate_trace_artifacts(trace["artifacts"])
            except ArtifactValidationError as exc:
                errors.append(exc.message)
            else:
                errors.extend(artifact_errors)
        return ValidationResult(not errors, tuple(errors))

    @staticmethod
    def _validate_run_record(trace: Mapping[str, Any], errors: list[str]) -> None:
        record = trace.get("run_record")
        if not isinstance(record, dict):
            errors.append("Trace run_record must be a mapping")
            return
        missing = sorted(REQUIRED_RUN_RECORD_FIELDS - set(record))
        if missing:
            errors.append(f"Missing Run Record fields: {', '.join(missing)}")
            return
        artifacts = trace.get("artifacts")
        artifact_refs = (
            sorted(artifacts.values())
            if isinstance(artifacts, dict)
            and all(isinstance(value, str) for value in artifacts.values())
            else []
        )
        expected = {
            "schema_version": "1.0",
            "run_id": trace.get("run_id"),
            "project_id": trace.get("project_id"),
            "skill_name": trace.get("skill"),
            "skill_version": trace.get("version"),
            "state": trace.get("final_state"),
            "input_refs": trace.get("input_refs"),
            "artifact_refs": artifact_refs,
            "trace_ref": "trace/execution_trace.json",
        }
        for field, value in expected.items():
            if record.get(field) != value:
                errors.append(f"Run Record field does not match trace: {field}")

    @staticmethod
    def _validate_run_refs(
        trace: Mapping[str, Any], run_root: Path, errors: list[str]
    ) -> None:
        input_dir = (run_root / "input").resolve()
        input_refs = trace.get("input_refs")
        if not isinstance(input_refs, list):
            return
        for value in input_refs:
            if not isinstance(value, str):
                errors.append("Input reference must be a string")
                continue
            candidate = Path(value)
            if candidate.is_absolute():
                errors.append("Input reference is absolute")
                continue
            resolved = (run_root / candidate).resolve()
            try:
                resolved.relative_to(run_root)
                resolved.relative_to(input_dir)
            except ValueError:
                errors.append("Input reference escapes the staged input directory")
                continue
            if not resolved.is_file():
                errors.append(f"Input reference is missing: {value}")

        record = trace.get("run_record")
        if isinstance(record, dict):
            trace_ref = record.get("trace_ref")
            if isinstance(trace_ref, str):
                resolved_trace = (run_root / trace_ref).resolve()
                try:
                    resolved_trace.relative_to(run_root)
                    resolved_trace.relative_to((run_root / "trace").resolve())
                except ValueError:
                    errors.append("Run Record trace_ref escapes the trace directory")
                else:
                    if not resolved_trace.is_file():
                        errors.append("Run Record trace_ref is missing")
