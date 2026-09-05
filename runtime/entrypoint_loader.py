"""Resolve and invoke registered Skill entrypoints inside the Skill boundary."""

from __future__ import annotations

import importlib
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from .capabilities import CapabilitySet
from .models import (
    AgentRuntimeError,
    EntrypointSpec,
    LoadedSkill,
    RunContext,
    SkillEntrypoint,
    SkillExecutionResult,
)


class EntrypointLoader:
    """Load a Skill module through a temporary, isolated package namespace."""

    def load(self, skill: LoadedSkill) -> SkillEntrypoint:
        spec = skill.contract.entrypoint
        if spec is None:
            raise AgentRuntimeError(
                f"Active Skill has no entrypoint: {skill.name}",
                code="ACTIVE_SKILL_ENTRYPOINT_MISSING",
            )
        python_root = _resolve_python_root(skill.skill_path, spec.python_path)
        _validate_module_name(spec.module)
        module_file = _resolve_declared_module_file(
            python_root, spec.module, skill.skill_path
        )

        def invoke(
            context: RunContext,
            loaded_skill: LoadedSkill,
            capabilities: CapabilitySet,
        ) -> SkillExecutionResult:
            return self._invoke(
                python_root,
                module_file,
                spec,
                context,
                loaded_skill,
                capabilities,
            )

        return invoke

    @staticmethod
    def _invoke(
        python_root: Path,
        expected_module_file: Path,
        spec: EntrypointSpec,
        context: RunContext,
        skill: LoadedSkill,
        capabilities: CapabilitySet,
    ) -> SkillExecutionResult:
        namespace = f"_agent_os_skill_{uuid4().hex}"
        qualified_name = f"{namespace}.{spec.module}"
        original_sys_path = list(sys.path)
        root_package = ModuleType(namespace)
        root_package.__path__ = [str(python_root)]  # type: ignore[attr-defined]
        root_package.__package__ = namespace
        root_spec = ModuleSpec(namespace, loader=None, is_package=True)
        root_spec.submodule_search_locations = [str(python_root)]
        root_package.__spec__ = root_spec
        sys.modules[namespace] = root_package
        try:
            try:
                module = importlib.import_module(qualified_name)
            except ModuleNotFoundError as exc:
                code = (
                    "ENTRYPOINT_MODULE_NOT_FOUND"
                    if exc.name == qualified_name
                    or (exc.name and qualified_name.startswith(f"{exc.name}."))
                    else "ENTRYPOINT_IMPORT_FAILED"
                )
                raise AgentRuntimeError(
                    f"Unable to import Skill entrypoint module {spec.module!r}: {exc}",
                    code=code,
                ) from exc
            except Exception as exc:
                raise AgentRuntimeError(
                    f"Unable to import Skill entrypoint module {spec.module!r}: {exc}",
                    code="ENTRYPOINT_IMPORT_FAILED",
                ) from exc

            _verify_namespace_files(namespace, skill.skill_path)
            imported_module_file = getattr(module, "__file__", None)
            if imported_module_file is None or Path(imported_module_file).resolve() != (
                expected_module_file
            ):
                raise AgentRuntimeError(
                    f"Imported module does not match declared entrypoint: {spec.module}",
                    code="ENTRYPOINT_MODULE_MISMATCH",
                )
            candidate = getattr(module, spec.callable, None)
            if not callable(candidate):
                raise AgentRuntimeError(
                    "Skill entrypoint callable is missing or not callable: "
                    f"{spec.module}.{spec.callable}",
                    code="ENTRYPOINT_CALLABLE_INVALID",
                )
            return candidate(context, skill, capabilities)
        finally:
            sys.path[:] = original_sys_path
            for module_name in tuple(sys.modules):
                if module_name == namespace or module_name.startswith(f"{namespace}."):
                    sys.modules.pop(module_name, None)


def _resolve_python_root(skill_root: Path, declared_path: str) -> Path:
    raw_path = Path(declared_path)
    if raw_path.is_absolute() or ".." in raw_path.parts:
        raise AgentRuntimeError(
            f"Entrypoint python_path escapes Skill root: {declared_path}",
            code="ENTRYPOINT_PATH_ESCAPE",
        )
    resolved_skill_root = skill_root.resolve()
    resolved_python_root = (resolved_skill_root / raw_path).resolve()
    try:
        resolved_python_root.relative_to(resolved_skill_root)
    except ValueError as exc:
        raise AgentRuntimeError(
            f"Entrypoint python_path escapes Skill root: {declared_path}",
            code="ENTRYPOINT_PATH_ESCAPE",
        ) from exc
    if not resolved_python_root.is_dir():
        raise AgentRuntimeError(
            f"Entrypoint python_path does not exist: {resolved_python_root}",
            code="ENTRYPOINT_PATH_MISSING",
        )
    return resolved_python_root


def _validate_module_name(module_name: str) -> None:
    if not module_name or any(
        not component.isidentifier() for component in module_name.split(".")
    ):
        raise AgentRuntimeError(
            f"Entrypoint module name is invalid: {module_name!r}",
            code="ENTRYPOINT_MODULE_INVALID",
        )


def _resolve_declared_module_file(
    python_root: Path, module_name: str, skill_root: Path
) -> Path:
    components = module_name.split(".")
    package_root = python_root
    for component in components[:-1]:
        package_root = package_root / component
        _require_inside_skill(package_root, skill_root)
        if not package_root.is_dir():
            raise AgentRuntimeError(
                f"Entrypoint package does not exist: {module_name}",
                code="ENTRYPOINT_MODULE_NOT_FOUND",
            )
        package_initializer = package_root / "__init__.py"
        if package_initializer.exists():
            _require_inside_skill(package_initializer, skill_root)

    module_path = package_root / f"{components[-1]}.py"
    package_initializer = package_root / components[-1] / "__init__.py"
    if module_path.is_file():
        return _require_inside_skill(module_path, skill_root)
    if package_initializer.is_file():
        return _require_inside_skill(package_initializer, skill_root)
    raise AgentRuntimeError(
        f"Entrypoint module does not exist: {module_name}",
        code="ENTRYPOINT_MODULE_NOT_FOUND",
    )


def _require_inside_skill(path: Path, skill_root: Path) -> Path:
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(skill_root.resolve())
    except ValueError as exc:
        raise AgentRuntimeError(
            f"Entrypoint module path escapes Skill root: {resolved_path}",
            code="ENTRYPOINT_MODULE_ESCAPE",
        ) from exc
    return resolved_path


def _verify_namespace_files(namespace: str, skill_root: Path) -> None:
    resolved_skill_root = skill_root.resolve()
    for module_name, module in tuple(sys.modules.items()):
        if module_name != namespace and not module_name.startswith(f"{namespace}."):
            continue
        module_file = getattr(module, "__file__", None)
        if module_file is None:
            continue
        _require_inside_skill(Path(module_file), resolved_skill_root)
