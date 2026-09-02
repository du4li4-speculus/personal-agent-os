"""Load a registered Skill's executable contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Tuple

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

from .models import (
    DependencyError,
    LoadedSkill,
    RegistryEntry,
    SkillLoadError,
)
from .registry_loader import RegistryLoader


class SkillLoader:
    """Load ``SKILL.md`` and ``manifest.yaml`` for a registered Skill."""

    def __init__(self, registry_loader: RegistryLoader) -> None:
        self.registry_loader = registry_loader

    def load(self, skill_name: str) -> LoadedSkill:
        entry = self.registry_loader.get(skill_name)
        skill_dir = entry.resolved_path
        definition_path = skill_dir / "SKILL.md"
        manifest_path = skill_dir / "manifest.yaml"
        if not definition_path.is_file():
            raise SkillLoadError(
                f"Skill definition does not exist: {definition_path}",
                code="SKILL_DEFINITION_MISSING",
            )
        if not manifest_path.is_file():
            raise SkillLoadError(
                f"Skill manifest does not exist: {manifest_path}",
                code="SKILL_MANIFEST_MISSING",
            )

        try:
            definition = definition_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SkillLoadError(f"Unable to read Skill definition: {definition_path}") from exc
        manifest = _read_manifest(manifest_path)
        name = _required_string(manifest, "name", manifest_path)
        version = _required_string(manifest, "version", manifest_path)
        skill_type = _required_string(manifest, "type", manifest_path)
        if name != entry.name:
            raise SkillLoadError(
                f"Manifest name {name!r} does not match registry name {entry.name!r}",
                code="SKILL_NAME_MISMATCH",
            )
        if version != entry.version:
            raise SkillLoadError(
                f"Manifest version {version!r} does not match registry version {entry.version!r}",
                code="SKILL_VERSION_MISMATCH",
            )
        if skill_type != entry.skill_type:
            raise SkillLoadError(
                f"Manifest type {skill_type!r} does not match registry type {entry.skill_type!r}",
                code="SKILL_TYPE_MISMATCH",
            )

        outputs = _required_string_list(manifest, "outputs", manifest_path)
        for output in outputs:
            output_path = Path(output)
            if output_path.is_absolute() or ".." in output_path.parts:
                raise SkillLoadError(
                    f"Manifest output path is unsafe: {output}",
                    code="SKILL_OUTPUT_INVALID",
                )
        requires = _required_string_list(manifest, "requires", manifest_path)
        return LoadedSkill.create(
            name=name,
            version=version,
            skill_type=skill_type,
            skill_path=skill_dir,
            definition=definition,
            manifest=manifest,
            outputs=outputs,
            requires=requires,
        )


def _read_manifest(path: Path) -> Mapping[str, Any]:
    if yaml is None:
        raise DependencyError(
            "PyYAML is required to load Agent OS YAML contracts"
        ) from _YAML_IMPORT_ERROR
    try:
        with path.open("r", encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle)
    except Exception as exc:
        raise SkillLoadError(f"Unable to parse Skill manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise SkillLoadError(f"Skill manifest must be a mapping: {path}")
    return manifest


def _required_string(manifest: Mapping[str, Any], key: str, path: Path) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SkillLoadError(f"Manifest field {key!r} must be a non-empty string: {path}")
    return value


def _required_string_list(
    manifest: Mapping[str, Any], key: str, path: Path
) -> Tuple[str, ...]:
    value = manifest.get(key)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise SkillLoadError(f"Manifest field {key!r} must be a string list: {path}")
    return tuple(value)
