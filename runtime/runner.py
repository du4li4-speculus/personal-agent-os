"""Orchestrate registered Skills inside isolated Project run boundaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .artifact_manager import ArtifactManager
from .capabilities import CapabilitySet
from .entrypoint_loader import EntrypointLoader
from .execution_logger import ExecutionLogger
from .models import (
    AgentRuntimeError,
    CapabilityProvider,
    ExecutionError,
    InputRef,
    LoadedSkill,
    RunContext,
    RunResult,
    RuntimeReadinessError,
    SkillExecutionResult,
)
from .project_loader import ProjectLoader
from .registry_loader import RegistryLoader
from .run_store import RunStore
from .skill_loader import SkillLoader
from .state_manager import StateManager
from .validator_engine import ValidatorEngine


class AgentRuntime:
    """Run one Project-authorized, registered Skill in a fresh run directory."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.registry_loader = RegistryLoader(self.repository_root)
        self.project_loader = ProjectLoader(
            self.repository_root, registry_loader=self.registry_loader
        )
        self.skill_loader = SkillLoader(self.registry_loader)
        self.entrypoint_loader = EntrypointLoader()
        self.state_machine_path = self.repository_root / "runtime" / "state_machine.yaml"
        self.validator = ValidatorEngine()

    def run(
        self,
        *,
        task: str,
        skill_name: str,
        project_id: str,
        inputs: Sequence[InputRef],
        run_root: Path,
        capabilities: Mapping[str, CapabilityProvider],
    ) -> RunResult:
        run_id = uuid4().hex
        try:
            project = self.project_loader.load(project_id)
            if skill_name not in project.allowed_skills:
                raise AgentRuntimeError(
                    f"Skill is not allowed by Project {project_id}: {skill_name}",
                    code="PROJECT_SKILL_NOT_ALLOWED",
                )
            run_store = RunStore(Path(run_root))
            run_paths = run_store.create(project_id, run_id)
            staged_inputs = run_store.stage_inputs(run_paths, inputs)
        except AgentRuntimeError as exc:
            return RunResult(
                run_id=run_id,
                status="FAILED",
                final_state="FAILED",
                trace_path=None,
                validation_errors=(f"{exc.code}: {exc.message}",),
            )

        context = RunContext.create(
            run_id=run_id,
            task=task,
            skill_name=skill_name,
            project_id=project_id,
            repository_root=self.repository_root,
            run_paths=run_paths,
            inputs=staged_inputs,
        )
        capability_set = CapabilitySet(capabilities)
        state_manager = StateManager.from_file(self.state_machine_path)
        logger = ExecutionLogger(context)
        logger.record_transition(None, "CREATED", reason="run_created")

        try:
            self._move(state_manager, logger, "IDENTIFY_TASK", "task_identified")
            self._require_task(context.task)
            logger.record_step(
                "IDENTIFY_TASK",
                "success",
                details={
                    "task": context.task,
                    "project_id": context.project_id,
                    "input_count": len(context.inputs),
                },
            )

            self._move(state_manager, logger, "FIND_SKILL", "skill_lookup")
            registry_entry = self.registry_loader.get(context.skill_name)
            logger.record_step(
                "FIND_SKILL",
                "success",
                details={"registry_path": registry_entry.path},
            )

            self._move(state_manager, logger, "LOAD_SKILL", "skill_contract_load")
            skill = self.skill_loader.load(context.skill_name)
            entrypoint = self.entrypoint_loader.load(skill)
            logger.set_skill_version(skill.version)
            logger.set_proof(skill_loaded=True)
            logger.record_step(
                "LOAD_SKILL",
                "success",
                details={
                    "skill_version": skill.version,
                    "outputs": list(skill.outputs),
                },
            )

            self._move(state_manager, logger, "RUNTIME_CHECK", "runtime_readiness")
            self._runtime_check_with_recovery(
                context, skill, capability_set, state_manager, logger
            )

            self._move(state_manager, logger, "EXECUTE", "skill_entrypoint_execution")
            try:
                execution_result = entrypoint(context, skill, capability_set)
            except AgentRuntimeError:
                raise
            except Exception as exc:
                raise ExecutionError(f"Skill entrypoint failed: {exc}") from exc
            if not isinstance(execution_result, SkillExecutionResult):
                raise ExecutionError(
                    "Skill entrypoint must return SkillExecutionResult",
                    code="SKILL_RESULT_INVALID",
                )
            if not isinstance(execution_result.artifacts, Mapping) or not isinstance(
                execution_result.intermediate_artifacts, Mapping
            ):
                raise ExecutionError(
                    "SkillExecutionResult artifact collections must be mappings",
                    code="SKILL_RESULT_INVALID",
                )
            logger.record_step(
                "EXECUTE",
                "success",
                details={
                    "returned_artifacts": sorted(execution_result.artifacts.keys()),
                    "intermediate_artifacts": sorted(
                        execution_result.intermediate_artifacts.keys()
                    ),
                    "metadata_keys": sorted(execution_result.metadata.keys()),
                },
            )

            self._move(state_manager, logger, "ARTIFACT", "artifact_gate")
            intermediate_artifacts = ArtifactManager(
                context.work_dir, run_root=context.run_root
            ).validate(
                tuple(spec.path for spec in skill.contract.intermediate_outputs),
                execution_result.intermediate_artifacts,
            )
            artifacts = ArtifactManager(
                context.artifact_dir, run_root=context.run_root
            ).validate(skill.outputs, execution_result.artifacts)
            logger.set_artifacts(artifacts)
            logger.record_step(
                "ARTIFACT",
                "success",
                details={
                    "intermediate_artifacts": intermediate_artifacts,
                    "artifacts": artifacts,
                },
            )

            self._move(state_manager, logger, "VALIDATE", "validation_gate")
            logger.record_step("VALIDATE", "started")
            logger.persist()
            validation = self.validator.validate_trace(
                logger.as_dict(),
                run_root=context.run_root,
                require_deliverable=False,
            )
            if not validation.valid:
                raise AgentRuntimeError(
                    "Execution trace validation failed: "
                    + "; ".join(validation.errors),
                    code="TRACE_VALIDATION_FAILED",
                )
            logger.set_proof(validation_completed=True)
            logger.record_step("VALIDATE", "success")

            self._move(state_manager, logger, "DELIVER", "delivery_ready")
            logger.finish(status="SUCCEEDED", final_state="DELIVER")
            trace_path = logger.persist()
            return RunResult(
                run_id=context.run_id,
                status="SUCCEEDED",
                final_state="DELIVER",
                trace_path=trace_path,
                artifacts=artifacts,
            )
        except AgentRuntimeError as exc:
            return self._fail(context, state_manager, logger, exc)
        except Exception as exc:
            runtime_error = AgentRuntimeError(f"Unexpected runtime failure: {exc}")
            return self._fail(context, state_manager, logger, runtime_error)

    @staticmethod
    def _require_task(task: str) -> None:
        if not isinstance(task, str) or not task.strip():
            raise AgentRuntimeError(
                "Task must be a non-empty string", code="TASK_INVALID"
            )

    @staticmethod
    def _move(
        state_manager: StateManager,
        logger: ExecutionLogger,
        target: str,
        reason: str,
    ) -> None:
        previous = state_manager.current_state
        state_manager.transition(target)
        logger.record_transition(previous, target, reason=reason)

    @staticmethod
    def _runtime_check(
        context: RunContext,
        skill: LoadedSkill,
        capabilities: CapabilitySet,
    ) -> None:
        root = context.run_root.resolve()
        directories = (
            context.input_dir,
            context.work_dir,
            context.artifact_dir,
            context.trace_dir,
            context.memory_dir,
        )
        for directory in directories:
            resolved = directory.resolve()
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise RuntimeReadinessError(
                    f"Run directory escapes current run: {directory}",
                    code="RUN_PATH_ESCAPE",
                    recoverable=False,
                ) from exc
            if not resolved.is_dir():
                raise RuntimeReadinessError(
                    f"Run path is not a directory: {directory}",
                    code="RUN_DIRECTORY_INVALID",
                    recoverable=False,
                )
            try:
                probe = resolved / ".runtime-write-probe"
                probe.write_text("runtime probe\n", encoding="utf-8")
                probe.unlink()
            except OSError as exc:
                raise RuntimeReadinessError(
                    f"Run directory is not writable: {directory}",
                    code="RUN_DIRECTORY_NOT_WRITABLE",
                ) from exc

        for input_ref in context.inputs:
            resolved_input = input_ref.path.resolve()
            try:
                resolved_input.relative_to(context.input_dir.resolve())
            except ValueError as exc:
                raise AgentRuntimeError(
                    "Skill input is outside the staged input boundary",
                    code="INPUT_PATH_ESCAPE",
                ) from exc
            if not resolved_input.is_file():
                raise AgentRuntimeError(
                    f"Staged input path does not exist: {resolved_input}",
                    code="INPUT_NOT_FOUND",
                )
        missing_capabilities = sorted(
            capability_id
            for capability_id in skill.contract.required_capabilities
            if not capabilities.has(capability_id)
        )
        if missing_capabilities:
            raise AgentRuntimeError(
                "Required runtime capabilities are unavailable: "
                + ", ".join(missing_capabilities),
                code="RUNTIME_CAPABILITY_MISSING",
            )

    def _runtime_check_with_recovery(
        self,
        context: RunContext,
        skill: LoadedSkill,
        capabilities: CapabilitySet,
        state_manager: StateManager,
        logger: ExecutionLogger,
    ) -> None:
        while True:
            try:
                self._runtime_check(context, skill, capabilities)
                logger.set_proof(runtime_checked=True)
                logger.record_step("RUNTIME_CHECK", "success")
                return
            except RuntimeReadinessError as exc:
                logger.record_step(
                    "RUNTIME_CHECK",
                    "failed",
                    error_code=exc.code,
                    error_message=exc.message,
                )
                if not exc.recoverable or not state_manager.can_recover():
                    raise
                self._move(state_manager, logger, "RECOVERY", "runtime_retry")
                logger.record_step(
                    "RECOVERY",
                    "success",
                    details={"attempt": state_manager.recovery_attempts},
                )
                self._move(state_manager, logger, "RUNTIME_CHECK", "retry_runtime_check")

    @staticmethod
    def _fail(
        context: RunContext,
        state_manager: StateManager,
        logger: ExecutionLogger,
        error: AgentRuntimeError,
    ) -> RunResult:
        logger.record_step(
            "FAILURE",
            "failed",
            error_code=error.code,
            error_message=error.message,
        )
        if not state_manager.is_terminal():
            previous = state_manager.current_state
            try:
                state_manager.transition("FAILED")
                logger.record_transition(previous, "FAILED", reason=error.code)
            except AgentRuntimeError as transition_error:
                logger.errors.append(
                    {
                        "code": transition_error.code,
                        "message": transition_error.message,
                    }
                )
        logger.finish(status="FAILED", final_state=state_manager.current_state)
        trace_path: Optional[Path]
        try:
            trace_path = logger.persist()
        except (OSError, AgentRuntimeError):
            trace_path = None
        return RunResult(
            run_id=context.run_id,
            status="FAILED",
            final_state=state_manager.current_state,
            trace_path=trace_path,
            artifacts=logger.artifacts,
            validation_errors=(f"{error.code}: {error.message}",),
        )
