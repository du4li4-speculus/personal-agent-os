"""Persist schema-valid Memory Candidates inside one run only."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .contract_validator import ContractValidator
from .models import AgentRuntimeError, RunPaths
from .run_store import _require_within, _write_json_atomic


class MemoryManager:
    """Write one proposed candidate without exposing persistent Memory APIs."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.contract_validator = ContractValidator(self.repository_root)

    def write_candidate(
        self, paths: RunPaths, payload: Mapping[str, Any]
    ) -> Path:
        candidate = dict(payload)
        violations = self.contract_validator.validate(
            candidate,
            self.repository_root / "contracts" / "memory-candidate.schema.json",
        )
        if violations:
            violation = violations[0]
            raise AgentRuntimeError(
                "Memory Candidate contract violation at "
                f"{violation.path} ({violation.keyword}): {violation.message}",
                code="MEMORY_CANDIDATE_SCHEMA_INVALID",
            )
        if candidate["project_id"] != paths.root.parent.name:
            raise AgentRuntimeError(
                "Memory Candidate project does not match the run boundary",
                code="MEMORY_CANDIDATE_PROJECT_MISMATCH",
            )
        if candidate["run_id"] != paths.root.name:
            raise AgentRuntimeError(
                "Memory Candidate run does not match the run boundary",
                code="MEMORY_CANDIDATE_RUN_MISMATCH",
            )

        resolved_run_root = paths.root.resolve()
        resolved_memory_dir = paths.memory_dir.resolve()
        try:
            _require_within(
                resolved_memory_dir,
                resolved_run_root,
                "MEMORY_CANDIDATE_PATH_ESCAPE",
            )
        except AgentRuntimeError as exc:
            raise AgentRuntimeError(
                f"Memory Candidate directory escapes the run: {paths.memory_dir}",
                code="MEMORY_CANDIDATE_PATH_ESCAPE",
            ) from exc
        if not resolved_memory_dir.is_dir():
            raise AgentRuntimeError(
                f"Memory Candidate directory is missing: {resolved_memory_dir}",
                code="MEMORY_CANDIDATE_PATH_MISSING",
            )
        for evidence_ref in candidate["evidence_refs"]:
            evidence_path = (resolved_run_root / evidence_ref).resolve()
            try:
                _require_within(
                    evidence_path,
                    resolved_run_root,
                    "MEMORY_CANDIDATE_EVIDENCE_ESCAPE",
                )
            except AgentRuntimeError as exc:
                raise AgentRuntimeError(
                    f"Memory Candidate evidence escapes the run: {evidence_ref}",
                    code="MEMORY_CANDIDATE_EVIDENCE_ESCAPE",
                ) from exc
            if not evidence_path.is_file():
                raise AgentRuntimeError(
                    f"Memory Candidate evidence does not exist: {evidence_ref}",
                    code="MEMORY_CANDIDATE_EVIDENCE_MISSING",
                )

        candidate_path = resolved_memory_dir / "memory_candidate.json"
        _require_within(
            candidate_path.resolve(),
            resolved_run_root,
            "MEMORY_CANDIDATE_PATH_ESCAPE",
        )
        _write_json_atomic(candidate_path, candidate)
        return candidate_path
