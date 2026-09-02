"""Validate execution proof and persisted artifact references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .artifact_manager import ArtifactManager
from .models import ValidationResult


REQUIRED_TRACE_FIELDS = {
    "run_id",
    "task",
    "skill",
    "version",
    "started_at",
    "finished_at",
    "transitions",
    "steps",
    "artifacts",
    "proof",
    "status",
    "final_state",
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
        try:
            with trace_path.open("r", encoding="utf-8") as handle:
                trace = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return ValidationResult(False, (f"Unable to read trace: {exc}",))
        return self.validate_trace(trace, output_dir=trace_path.parent)

    def validate_trace(
        self,
        trace: Mapping[str, Any],
        *,
        output_dir: Path | None = None,
        require_deliverable: bool = True,
    ) -> ValidationResult:
        errors: list[str] = []
        missing = sorted(REQUIRED_TRACE_FIELDS - set(trace.keys()))
        if missing:
            errors.append(f"Missing trace fields: {', '.join(missing)}")
            return ValidationResult(False, tuple(errors))

        for field in ("run_id", "task", "skill", "version", "started_at"):
            if not isinstance(trace[field], str) or not trace[field].strip():
                errors.append(f"Trace field must be a non-empty string: {field}")
        if require_deliverable:
            if trace["status"] != "SUCCEEDED":
                errors.append(f"Trace is not successful: {trace['status']}")
            if trace["final_state"] != "DELIVER":
                errors.append(f"Trace did not reach DELIVER: {trace['final_state']}")
            if not isinstance(trace["finished_at"], str) or not trace["finished_at"].strip():
                errors.append("A deliverable trace must have finished_at")
        elif trace["status"] not in {"RUNNING", "SUCCEEDED"}:
            errors.append(f"In-progress trace has invalid status: {trace['status']}")
        if not isinstance(trace["steps"], list) or not trace["steps"]:
            errors.append("Trace steps must be a non-empty list")
        if not isinstance(trace["transitions"], list) or not trace["transitions"]:
            errors.append("Trace transitions must be a non-empty list")
        if not isinstance(trace["artifacts"], dict):
            errors.append("Trace artifacts must be a mapping")
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

        if trace.get("transitions"):
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

        if output_dir is not None and isinstance(trace.get("artifacts"), dict):
            artifact_errors = ArtifactManager(output_dir).validate_trace_artifacts(
                trace["artifacts"]
            )
            errors.extend(artifact_errors)
        return ValidationResult(not errors, tuple(errors))
