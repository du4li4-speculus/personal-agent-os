"""Load a registered Skill's executable contract."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Tuple

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

from .models import (
    ArtifactSpec,
    DependencyError,
    EntrypointSpec,
    LoadedSkill,
    RegistryEntry,
    SkillManifest,
    SkillLoadError,
)
from .registry_loader import RegistryLoader


class SkillLoader:
    """Load ``SKILL.md`` and ``manifest.yaml`` for a registered Skill."""

    def __init__(self, registry_loader: RegistryLoader) -> None:
        self.registry_loader = registry_loader
        self.contract_validator = registry_loader.contract_validator

    def load(self, skill_name: str) -> LoadedSkill:
        entry = self.registry_loader.get(skill_name)
        return self._load_entry(entry)

    def load_registered(self, skill_name: str) -> LoadedSkill:
        """Validate a registered Skill without granting execution authority."""

        entry = self.registry_loader.get_registered(skill_name)
        return self._load_entry(entry)

    def _load_entry(self, entry: RegistryEntry) -> LoadedSkill:
        skill_dir = entry.resolved_path
        definition_path = skill_dir / "SKILL.md"
        manifest_path = _resolve_skill_reference(
            skill_dir,
            entry.manifest,
            code="SKILL_MANIFEST_PATH_ESCAPE",
            label="manifest",
        )
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
        violations = self.contract_validator.validate(
            manifest,
            self.registry_loader.repository_root
            / "contracts"
            / "skill-manifest.schema.json",
        )
        if violations:
            violation = violations[0]
            if (
                violation.path == "$.entrypoint.python_path"
                and violation.keyword == "not"
            ):
                raise SkillLoadError(
                    f"Entrypoint python_path escapes Skill root: {violation.message}",
                    code="ENTRYPOINT_PATH_ESCAPE",
                )
            raise SkillLoadError(
                "Skill manifest contract violation at "
                f"{violation.path} ({violation.keyword}): {violation.message}",
                code="SKILL_MANIFEST_SCHEMA_INVALID",
            )

        contract = _manifest_from_mapping(manifest)
        if contract.name != entry.name:
            raise SkillLoadError(
                f"Manifest name {contract.name!r} does not match registry name {entry.name!r}",
                code="SKILL_NAME_MISMATCH",
            )
        if contract.version != entry.version:
            raise SkillLoadError(
                "Manifest version "
                f"{contract.version!r} does not match registry version {entry.version!r}",
                code="SKILL_VERSION_MISMATCH",
            )
        if entry.status == "active" and contract.entrypoint is None:
            raise SkillLoadError(
                f"Active Skill has no entrypoint: {entry.name}",
                code="ACTIVE_SKILL_ENTRYPOINT_MISSING",
            )

        _require_skill_file(skill_dir, contract.inputs["contract"], "input contract")
        for artifact in (*contract.intermediate_outputs, *contract.outputs):
            _assert_safe_relative_path(
                artifact.path, code="SKILL_OUTPUT_INVALID", label="artifact path"
            )
            if artifact.schema is not None:
                _require_skill_file(skill_dir, artifact.schema, "artifact schema")
        if contract.entrypoint is not None:
            entrypoint_root = _resolve_skill_reference(
                skill_dir,
                contract.entrypoint.python_path,
                code="ENTRYPOINT_PATH_ESCAPE",
                label="entrypoint python_path",
            )
            if not entrypoint_root.is_dir():
                raise SkillLoadError(
                    f"Entrypoint python_path does not exist: {entrypoint_root}",
                    code="SKILL_ENTRYPOINT_PATH_MISSING",
                )

        outputs = tuple(artifact.path for artifact in contract.outputs)
        return LoadedSkill.create(
            name=contract.name,
            version=contract.version,
            skill_type=contract.kind,
            skill_path=skill_dir,
            definition=definition,
            manifest=manifest,
            contract=contract,
            outputs=outputs,
            requires=contract.required_capabilities,
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


def _manifest_from_mapping(manifest: Mapping[str, Any]) -> SkillManifest:
    raw_entrypoint = manifest.get("entrypoint")
    entrypoint = (
        EntrypointSpec(
            python_path=raw_entrypoint["python_path"],
            module=raw_entrypoint["module"],
            callable=raw_entrypoint["callable"],
        )
        if raw_entrypoint is not None
        else None
    )
    capabilities = manifest["capabilities"]
    return SkillManifest(
        name=manifest["name"],
        version=manifest["version"],
        kind=manifest["kind"],
        entrypoint=entrypoint,
        inputs=MappingProxyType(dict(manifest["inputs"])),
        intermediate_outputs=_artifact_specs(manifest["intermediate_outputs"]),
        outputs=_artifact_specs(manifest["outputs"]),
        required_capabilities=tuple(capabilities["required"]),
        optional_capabilities=tuple(capabilities["optional"]),
        cognition=MappingProxyType(dict(manifest["cognition"])),
    )


def _artifact_specs(raw_artifacts: Any) -> Tuple[ArtifactSpec, ...]:
    return tuple(
        ArtifactSpec(name=item["name"], path=item["path"], schema=item.get("schema"))
        for item in raw_artifacts
    )


def _assert_safe_relative_path(value: str, *, code: str, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SkillLoadError(f"Unsafe {label}: {value}", code=code)
    return path


def _resolve_skill_reference(
    skill_dir: Path, value: str, *, code: str, label: str
) -> Path:
    relative = _assert_safe_relative_path(value, code=code, label=label)
    resolved = (skill_dir / relative).resolve()
    try:
        resolved.relative_to(skill_dir.resolve())
    except ValueError as exc:
        raise SkillLoadError(f"{label} escapes Skill root: {value}", code=code) from exc
    return resolved


def _require_skill_file(skill_dir: Path, value: str, label: str) -> Path:
    resolved = _resolve_skill_reference(
        skill_dir, value, code="SKILL_SCHEMA_PATH_ESCAPE", label=label
    )
    if not resolved.is_file():
        raise SkillLoadError(
            f"Declared {label} does not exist: {resolved}",
            code="SKILL_SCHEMA_MISSING",
        )
    return resolved
