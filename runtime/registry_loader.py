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
        self._entries: Dict[str, RegistryEntry] | None = None

    def load(self) -> Mapping[str, RegistryEntry]:
        if self._entries is not None:
            return self._entries
        document = _read_yaml(self.registry_path)
        if not isinstance(document, dict) or not isinstance(document.get("skills"), dict):
            raise RegistryError("Registry must contain a top-level 'skills' mapping")

        entries: Dict[str, RegistryEntry] = {}
        for name, raw in document["skills"].items():
            if not isinstance(name, str) or not name.strip():
                raise RegistryError("Every registry skill key must be a non-empty string")
            if not isinstance(raw, dict):
                raise RegistryError(f"Registry entry for {name!r} must be a mapping")
            entry = _entry_from_mapping(name, raw, self.skills_root)
            if name in entries:
                raise RegistryError(f"Duplicate registry skill: {name}")
            entries[name] = entry
        self._entries = entries
        return entries

    def get(self, skill_name: str) -> RegistryEntry:
        entries = self.load()
        try:
            entry = entries[skill_name]
        except KeyError as exc:
            raise RegistryError(
                f"Skill is not registered: {skill_name}", code="SKILL_NOT_FOUND"
            ) from exc
        if entry.status != "active":
            raise RegistryError(
                f"Skill is not active: {skill_name} ({entry.status})",
                code="SKILL_NOT_ACTIVE",
            )
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
    name: str, raw: Mapping[str, Any], skills_root: Path
) -> RegistryEntry:
    required = ("version", "type", "status", "path")
    missing = [key for key in required if key not in raw]
    if missing:
        raise RegistryError(f"Registry entry {name!r} is missing: {', '.join(missing)}")
    values = {key: raw[key] for key in required}
    if any(not isinstance(values[key], str) or not values[key].strip() for key in required):
        raise RegistryError(f"Registry entry {name!r} has invalid string fields")

    relative_path = Path(values["path"])
    if relative_path.is_absolute():
        raise RegistryError(f"Skill path must be relative: {values['path']}")
    resolved = (skills_root.parent / relative_path).resolve()
    try:
        resolved.relative_to(skills_root)
    except ValueError as exc:
        raise RegistryError(f"Skill path escapes skills directory: {values['path']}") from exc
    if not resolved.is_dir():
        raise RegistryError(
            f"Skill directory does not exist: {resolved}", code="SKILL_PATH_MISSING"
        )

    return RegistryEntry(
        name=name,
        version=values["version"],
        skill_type=values["type"],
        status=values["status"],
        path=values["path"],
        resolved_path=resolved,
    )
