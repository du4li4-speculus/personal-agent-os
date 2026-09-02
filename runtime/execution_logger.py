"""Structured, atomic execution trace persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional

from .models import (
    ExecutionStep,
    ProofFlags,
    RunContext,
    StateTransition,
    utc_now,
)


class ExecutionLogger:
    """Build and persist one execution trace for a run."""

    def __init__(self, context: RunContext, *, skill_version: str = "unknown") -> None:
        self.context = context
        self.skill_version = skill_version
        self.started_at = utc_now()
        self.finished_at: Optional[str] = None
        self.status = "RUNNING"
        self.final_state = "CREATED"
        self.transitions: list[StateTransition] = []
        self.steps: list[ExecutionStep] = []
        self.artifacts: dict[str, str] = {}
        self.proof = ProofFlags()
        self.errors: list[dict[str, str]] = []
        self.trace_path = context.output_dir / "execution_trace.json"

    def set_skill_version(self, version: str) -> None:
        self.skill_version = version

    def record_transition(
        self,
        from_state: Optional[str],
        to_state: str,
        *,
        reason: Optional[str] = None,
    ) -> None:
        self.transitions.append(
            StateTransition(
                from_state=from_state,
                to_state=to_state,
                at=utc_now(),
                reason=reason,
            )
        )
        self.final_state = to_state

    def record_step(
        self,
        name: str,
        status: str,
        *,
        details: Optional[Mapping[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        step = ExecutionStep(
            name=name,
            status=status,
            at=utc_now(),
            details=dict(details or {}),
            error_code=error_code,
            error_message=error_message,
        )
        self.steps.append(step)
        if error_code or error_message:
            self.errors.append(
                {
                    "code": error_code or "RUNTIME_ERROR",
                    "message": error_message or "",
                }
            )

    def set_artifacts(self, artifacts: Mapping[str, str]) -> None:
        self.artifacts = dict(artifacts)
        self.proof.artifacts_validated = True

    def set_proof(self, **flags: bool) -> None:
        for name, value in flags.items():
            if not hasattr(self.proof, name):
                raise ValueError(f"Unknown proof flag: {name}")
            setattr(self.proof, name, bool(value))

    def finish(self, *, status: str, final_state: str) -> None:
        self.status = status
        self.final_state = final_state
        self.finished_at = utc_now()

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.context.run_id,
            "task": self.context.task,
            "skill": self.context.skill_name,
            "version": self.skill_version,
            "input_path": str(self.context.input_path) if self.context.input_path else None,
            "output_dir": str(self.context.output_dir),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "transitions": [transition.to_dict() for transition in self.transitions],
            "steps": [step.to_dict() for step in self.steps],
            "artifacts": dict(self.artifacts),
            "proof": self.proof.to_dict(),
            "status": self.status,
            "final_state": self.final_state,
            "errors": list(self.errors),
        }

    def persist(self) -> Path:
        """Write the current trace atomically and mark trace generation as proven."""

        self.context.output_dir.mkdir(parents=True, exist_ok=True)
        self.proof.execution_traced = True
        payload = json.dumps(self.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=".execution_trace.", suffix=".tmp", dir=str(self.context.output_dir)
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.trace_path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return self.trace_path
