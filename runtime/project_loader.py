"""Load non-sensitive declarative Project configuration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

from .contract_validator import ContractValidator
from .models import AgentRuntimeError, DependencyError, ProjectConfig
from .registry_loader import RegistryLoader


PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ProjectLoader:
    """Validate Project policy selection without granting domain ownership."""

    def __init__(
        self,
        repository_root: Path,
        registry_loader: RegistryLoader | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.projects_root = (self.repository_root / "projects").resolve()
        self.registry_loader = registry_loader or RegistryLoader(self.repository_root)
        self.contract_validator = ContractValidator(self.repository_root)

    def load(self, project_id: str) -> ProjectConfig:
        if not isinstance(project_id, str) or not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise AgentRuntimeError(
                f"Invalid Project id: {project_id!r}", code="PROJECT_ID_INVALID"
            )
        project_path = (self.projects_root / project_id / "project.yaml").resolve()
        try:
            project_path.relative_to(self.projects_root)
        except ValueError as exc:
            raise AgentRuntimeError(
                f"Project path escapes projects root: {project_id}",
                code="PROJECT_PATH_ESCAPE",
            ) from exc
        if not project_path.is_file():
            raise AgentRuntimeError(
                f"Project configuration does not exist: {project_path}",
                code="PROJECT_NOT_FOUND",
            )

        document = _read_yaml(project_path)
        violations = self.contract_validator.validate(
            document, self.repository_root / "contracts" / "project.schema.json"
        )
        if violations:
            violation = violations[0]
            raise AgentRuntimeError(
                "Project contract violation at "
                f"{violation.path} ({violation.keyword}): {violation.message}",
                code="PROJECT_SCHEMA_INVALID",
            )
        if document["project_id"] != project_id:
            raise AgentRuntimeError(
                "Project id does not match its directory: "
                f"{document['project_id']!r} != {project_id!r}",
                code="PROJECT_ID_MISMATCH",
            )
        for skill_name in document["allowed_skills"]:
            try:
                self.registry_loader.get_registered(skill_name)
            except AgentRuntimeError as exc:
                raise AgentRuntimeError(
                    f"Project references an unregistered Skill: {skill_name}",
                    code="PROJECT_SKILL_NOT_REGISTERED",
                ) from exc
        return ProjectConfig(
            schema_version=document["schema_version"],
            project_id=document["project_id"],
            allowed_skills=tuple(document["allowed_skills"]),
            cognition_mode=document["cognition_mode"],
            memory_policy=document["memory_policy"],
        )

    def list_project_ids(self) -> tuple[str, ...]:
        if not self.projects_root.is_dir():
            return ()
        return tuple(
            sorted(
                path.parent.name
                for path in self.projects_root.glob("*/project.yaml")
                if PROJECT_ID_PATTERN.fullmatch(path.parent.name)
            )
        )


def _read_yaml(path: Path) -> Any:
    if yaml is None:
        raise DependencyError(
            "PyYAML is required to load Agent OS Project contracts"
        ) from _YAML_IMPORT_ERROR
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except Exception as exc:
        raise AgentRuntimeError(
            f"Unable to parse Project configuration: {path}",
            code="PROJECT_YAML_INVALID",
        ) from exc
