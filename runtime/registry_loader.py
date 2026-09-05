"""Load and validate the Agent OS skill registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

from .contract_validator import ContractValidator
from .models import DependencyError, RegistryEntry, RegistryError


class RegistryLoader:
    """Discover active Skills from ``registry/skill_registry.yaml``."""

    def __init__(self, repository_root: Path, registry_path: Path | None = None) -> None:
        self.repository_root = repository_root.resolve()
        self.registry_path = (
            registry_path.resolve()
            if registry_path
            else self.repository_root / "registry" / "skill_registry.yaml"
        )
        self.skills_root = (self.repository_root / "skills").resolve()
        self.contract_validator = ContractValidator(self.repository_root)
        self._entries: Dict[str, RegistryEntry] | None = None

    def load(self) -> Mapping[str, RegistryEntry]:
        if self._entries is not None:
            return self._entries
        document = _read_yaml(self.registry_path)
        violations = self.contract_validator.validate(
            document,
            self.repository_root / "contracts" / "skill-registry.schema.json",
        )
        if violations:
            violation = violations[0]
            raise RegistryError(
                "Registry contract violation at "
                f"{violation.path} ({violation.keyword}): {violation.message}",
                code="REGISTRY_SCHEMA_INVALID",
            )

        schema_version = document["schema_version"]

        entries: Dict[str, RegistryEntry] = {}
        for name, raw in document["skills"].items():
            if not isinstance(name, str) or not name.strip():
                raise RegistryError("Every registry skill key must be a non-empty string")
            if not isinstance(raw, dict):
                raise RegistryError(f"Registry entry for {name!r} must be a mapping")
            entry = _entry_from_mapping(
                name, raw, self.skills_root, schema_version=schema_version
            )
            if name in entries:
                raise RegistryError(f"Duplicate registry skill: {name}")
            entries[name] = entry
        self._entries = entries
        return entries

    def get(self, skill_name: str) -> RegistryEntry:
        entry = self.get_registered(skill_name)
        if entry.status != "active":
            raise RegistryError(
                f"Skill is not active: {skill_name} ({entry.status})",
                code="SKILL_NOT_ACTIVE",
            )
        return entry

    def get_registered(self, skill_name: str) -> RegistryEntry:
        """Return a Registry entry without granting execution authority."""

        entries = self.load()
        try:
            entry = entries[skill_name]
        except KeyError as exc:
            raise RegistryError(
                f"Skill is not registered: {skill_name}", code="SKILL_NOT_FOUND"
            ) from exc
        return entry


def _read_yaml(path: Path) -> Any:
    if yaml is None:
        raise DependencyError(
            "PyYAML is required to load Agent OS YAML contracts"
        ) from _YAML_IMPORT_ERROR
    if not path.is_file():
        raise RegistryError(f"Registry file does not exist: {path}", code="REGISTRY_MISSING")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except Exception as exc:
        raise RegistryError(f"Unable to parse registry YAML: {path}") from exc


def _entry_from_mapping(
    name: str,
    raw: Mapping[str, Any],
    skills_root: Path,
    *,
    schema_version: str,
) -> RegistryEntry:
    relative_path = Path(raw["path"])
    if relative_path.is_absolute():
        raise RegistryError(f"Skill path must be relative: {raw['path']}")
    resolved = (skills_root.parent / relative_path).resolve()
    try:
        resolved.relative_to(skills_root)
    except ValueError as exc:
        raise RegistryError(f"Skill path escapes skills directory: {raw['path']}") from exc
    if not resolved.is_dir():
        raise RegistryError(
            f"Skill directory does not exist: {resolved}", code="SKILL_PATH_MISSING"
        )

    return RegistryEntry(
        schema_version=schema_version,
        name=name,
        version=raw["version"],
        status=raw["status"],
        path=raw["path"],
        manifest=raw["manifest"],
        resolved_path=resolved,
    )
