"""Data models and stable errors shared by runtime components."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Dict, Mapping, Optional, Tuple
from uuid import uuid4


CapabilityProvider = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


def utc_now() -> str:
    """Return a JSON-safe UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AgentRuntimeError(Exception):
    """Base exception with a stable code for execution traces."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "RUNTIME_ERROR",
        recoverable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.recoverable = recoverable


class DependencyError(AgentRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="RUNTIME_DEPENDENCY_MISSING")


class RegistryError(AgentRuntimeError):
    def __init__(self, message: str, *, code: str = "REGISTRY_INVALID") -> None:
        super().__init__(message, code=code)


class ContractError(AgentRuntimeError):
    def __init__(self, message: str, *, code: str = "CONTRACT_INVALID") -> None:
        super().__init__(message, code=code)


class SkillLoadError(AgentRuntimeError):
    def __init__(self, message: str, *, code: str = "SKILL_CONTRACT_INVALID") -> None:
        super().__init__(message, code=code)


class StateMachineError(AgentRuntimeError):
    def __init__(self, message: str, *, code: str = "STATE_MACHINE_INVALID") -> None:
        super().__init__(message, code=code)


class RuntimeReadinessError(AgentRuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "RUNTIME_NOT_READY",
        recoverable: bool = True,
    ) -> None:
        super().__init__(message, code=code, recoverable=recoverable)


class ExecutionError(AgentRuntimeError):
    def __init__(self, message: str, *, code: str = "EXECUTION_FAILED") -> None:
        super().__init__(message, code=code)


class ArtifactValidationError(AgentRuntimeError):
    def __init__(self, message: str, *, code: str = "ARTIFACT_INVALID") -> None:
        super().__init__(message, code=code)


class TraceValidationError(AgentRuntimeError):
    def __init__(self, message: str, *, code: str = "TRACE_INVALID") -> None:
        super().__init__(message, code=code)


@dataclass(frozen=True)
class RegistryEntry:
    schema_version: str
    name: str
    version: str
    status: str
    path: str
    manifest: str
    resolved_path: Path


@dataclass(frozen=True)
class EntrypointSpec:
    python_path: str
    module: str
    callable: str


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    path: str
    schema: Optional[str] = None


@dataclass(frozen=True)
class CapabilityRequirement:
    required: Tuple[str, ...]
    optional: Tuple[str, ...]


@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str
    kind: str
    entrypoint: Optional[EntrypointSpec]
    inputs: Mapping[str, Any]
    intermediate_outputs: Tuple[ArtifactSpec, ...]
    outputs: Tuple[ArtifactSpec, ...]
    required_capabilities: Tuple[str, ...]
    optional_capabilities: Tuple[str, ...]
    cognition: Mapping[str, Any]


@dataclass(frozen=True)
class ProjectConfig:
    schema_version: str
    project_id: str
    allowed_skills: Tuple[str, ...]
    cognition_mode: str
    memory_policy: str


@dataclass(frozen=True)
class RunRecord:
    schema_version: str
    run_id: str
    project_id: str
    skill_name: str
    skill_version: str
    state: str
    input_refs: Tuple[str, ...]
    artifact_refs: Tuple[str, ...]
    trace_ref: str


@dataclass(frozen=True)
class MemoryCandidate:
    schema_version: str
    candidate_id: str
    project_id: str
    run_id: str
    scope: str
    target_id: str
    proposition: str
    evidence_refs: Tuple[str, ...]
    status: str


@dataclass(frozen=True)
class AgentRole:
    schema_version: str
    name: str
    objective: str
    responsibility: str
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    constraints: Tuple[str, ...]
    evaluation_criteria: Tuple[str, ...]
    why_agent_required: str
    why_skill_insufficient: str


@dataclass(frozen=True)
class InputRef:
    path: Path
    role: str
    media_type: Optional[str] = None


@dataclass(frozen=True)
class LoadedSkill:
    name: str
    version: str
    skill_type: str
    skill_path: Path
    definition: str
    manifest: Mapping[str, Any]
    contract: SkillManifest
    outputs: Tuple[str, ...]
    requires: Tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        name: str,
        version: str,
        skill_type: str,
        skill_path: Path,
        definition: str,
        manifest: Mapping[str, Any],
        contract: SkillManifest,
        outputs: Tuple[str, ...],
        requires: Tuple[str, ...],
    ) -> "LoadedSkill":
        return cls(
            name=name,
            version=version,
            skill_type=skill_type,
            skill_path=skill_path,
            definition=definition,
            manifest=MappingProxyType(dict(manifest)),
            contract=contract,
            outputs=outputs,
            requires=requires,
        )


@dataclass(frozen=True)
class RunContext:
    run_id: str
    task: str
    skill_name: str
    project_id: str
    repository_root: Path
    output_dir: Path
    inputs: Tuple[InputRef, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        task: str,
        skill_name: str,
        project_id: str,
        repository_root: Path,
        output_dir: Path,
        inputs: Tuple[InputRef, ...] = (),
    ) -> "RunContext":
        return cls(
            run_id=str(uuid4()),
            task=task,
            skill_name=skill_name,
            project_id=project_id,
            repository_root=repository_root.resolve(),
            output_dir=output_dir.resolve(),
            inputs=tuple(
                InputRef(
                    path=Path(input_ref.path).resolve(),
                    role=input_ref.role,
                    media_type=input_ref.media_type,
                )
                for input_ref in inputs
            ),
        )

    @property
    def input_path(self) -> Optional[Path]:
        """Compatibility projection until Task 6 records all staged inputs."""

        return self.inputs[0].path if len(self.inputs) == 1 else None


@dataclass(frozen=True)
class SkillExecutionResult:
    intermediate_artifacts: Mapping[str, Path]
    artifacts: Mapping[str, Path]
    metadata: Mapping[str, Any] = field(default_factory=dict)


SkillEntrypoint = Callable[
    [RunContext, LoadedSkill, "CapabilitySet"],
    SkillExecutionResult,
]


@dataclass(frozen=True)
class StateTransition:
    from_state: Optional[str]
    to_state: str
    at: str
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "from": self.from_state,
            "to": self.to_state,
            "at": self.at,
        }
        if self.reason:
            data["reason"] = self.reason
        return data


@dataclass(frozen=True)
class ExecutionStep:
    name: str
    status: str
    at: str
    details: Mapping[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "at": self.at,
            "details": dict(self.details),
        }
        if self.error_code:
            data["error_code"] = self.error_code
        if self.error_message:
            data["error_message"] = self.error_message
        return data


@dataclass
class ProofFlags:
    skill_loaded: bool = False
    runtime_checked: bool = False
    execution_traced: bool = False
    artifacts_validated: bool = False
    validation_completed: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return {
            "skill_loaded": self.skill_loaded,
            "runtime_checked": self.runtime_checked,
            "execution_traced": self.execution_traced,
            "artifacts_validated": self.artifacts_validated,
            "validation_completed": self.validation_completed,
        }


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RunResult:
    run_id: str
    status: str
    final_state: str
    trace_path: Optional[Path]
    artifacts: Mapping[str, str] = field(default_factory=dict)
    validation_errors: Tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status == "SUCCEEDED" and self.final_state == "DELIVER"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "final_state": self.final_state,
            "trace_path": str(self.trace_path) if self.trace_path else None,
            "artifacts": dict(self.artifacts),
            "validation_errors": list(self.validation_errors),
        }
