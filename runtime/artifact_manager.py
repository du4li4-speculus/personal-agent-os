"""Validate adapter-produced artifacts against a Skill manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .models import ArtifactValidationError


class ArtifactManager:
    """Enforce exact, in-directory, non-empty manifest outputs."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir.resolve()

    def validate(
        self,
        declared_outputs: tuple[str, ...] | list[str],
        returned_artifacts: Mapping[str, str | Path],
    ) -> dict[str, str]:
        declared = set(declared_outputs)
        if len(declared) != len(declared_outputs):
            raise ArtifactValidationError(
                "Manifest contains duplicate artifact names",
                code="ARTIFACT_DECLARATION_DUPLICATE",
            )
        returned = set(returned_artifacts.keys())
        missing = sorted(declared - returned)
        extra = sorted(returned - declared)
        if missing:
            raise ArtifactValidationError(
                f"Missing declared artifacts: {', '.join(missing)}",
                code="ARTIFACT_MISSING",
            )
        if extra:
            raise ArtifactValidationError(
                f"Undeclared artifacts returned: {', '.join(extra)}",
                code="ARTIFACT_UNDECLARED",
            )

        normalized: dict[str, str] = {}
        for name in declared_outputs:
            value = returned_artifacts[name]
            raw_path = Path(value)
            if raw_path.is_absolute():
                raise ArtifactValidationError(
                    f"Artifact path must be relative to output directory: {name}",
                    code="ARTIFACT_PATH_ABSOLUTE",
                )
            resolved = (self.output_dir / raw_path).resolve()
            try:
                relative = resolved.relative_to(self.output_dir)
            except ValueError as exc:
                raise ArtifactValidationError(
                    f"Artifact path escapes output directory: {name}",
                    code="ARTIFACT_PATH_ESCAPE",
                ) from exc
            if not resolved.is_file():
                raise ArtifactValidationError(
                    f"Artifact is not a regular file: {name}",
                    code="ARTIFACT_NOT_FILE",
                )
            if resolved.stat().st_size <= 0:
                raise ArtifactValidationError(
                    f"Artifact is empty: {name}",
                    code="ARTIFACT_EMPTY",
                )
            normalized[name] = relative.as_posix()
        return normalized

    def validate_trace_artifacts(self, artifacts: Mapping[str, str]) -> tuple[str, ...]:
        """Check persisted artifact references without requiring the manifest."""

        errors: list[str] = []
        for name, value in artifacts.items():
            candidate = Path(value)
            if candidate.is_absolute():
                errors.append(f"{name}: artifact path is absolute")
                continue
            resolved = (self.output_dir / candidate).resolve()
            try:
                resolved.relative_to(self.output_dir)
            except ValueError:
                errors.append(f"{name}: artifact path escapes output directory")
                continue
            if not resolved.is_file():
                errors.append(f"{name}: artifact file is missing")
            elif resolved.stat().st_size <= 0:
                errors.append(f"{name}: artifact file is empty")
        return tuple(errors)
