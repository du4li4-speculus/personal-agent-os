"""Validate Agent OS documents against repository-owned JSON Schemas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence, Tuple

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    Draft202012Validator = None  # type: ignore[assignment]
    SchemaError = Exception  # type: ignore[assignment,misc]
    _JSONSCHEMA_IMPORT_ERROR = exc
else:
    _JSONSCHEMA_IMPORT_ERROR = None

from .models import ContractError, DependencyError


@dataclass(frozen=True)
class ContractViolation:
    """One deterministic schema violation suitable for tests and tooling."""

    code: str
    path: str
    schema_path: str
    keyword: str
    message: str


class ContractValidator:
    """Load Draft 2020-12 schemas only from explicitly allowed roots."""

    def __init__(
        self, repository_root: Path, *, additional_roots: Iterable[Path] = ()
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.allowed_roots = (
            self.repository_root,
            *(Path(root).resolve() for root in additional_roots),
        )

    def validate(
        self, document: Any, schema_path: Path
    ) -> Tuple[ContractViolation, ...]:
        if Draft202012Validator is None:
            raise DependencyError(
                "jsonschema is required to validate Agent OS contracts"
            ) from _JSONSCHEMA_IMPORT_ERROR

        resolved_schema_path = Path(schema_path).resolve()
        if not _is_within_any(resolved_schema_path, self.allowed_roots):
            raise ContractError(
                f"Schema path is outside an allowed contract root: {schema_path}",
                code="CONTRACT_SCHEMA_PATH_ESCAPE",
            )
        if not resolved_schema_path.is_file():
            raise ContractError(
                f"Contract schema does not exist: {resolved_schema_path}",
                code="CONTRACT_SCHEMA_MISSING",
            )

        try:
            schema = json.loads(resolved_schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(
                f"Unable to read contract schema: {resolved_schema_path}",
                code="CONTRACT_SCHEMA_UNREADABLE",
            ) from exc

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            raise ContractError(
                f"Invalid Draft 2020-12 schema: {resolved_schema_path}",
                code="CONTRACT_SCHEMA_INVALID",
            ) from exc

        validator = Draft202012Validator(schema)
        violations = [
            ContractViolation(
                code="CONTRACT_SCHEMA_VIOLATION",
                path=_json_path(error.absolute_path),
                schema_path=_json_path(error.absolute_schema_path),
                keyword=str(error.validator),
                message=error.message,
            )
            for error in validator.iter_errors(document)
        ]
        return tuple(
            sorted(
                violations,
                key=lambda item: (
                    item.path,
                    item.keyword,
                    item.schema_path,
                    item.message,
                ),
            )
        )


def _is_within_any(path: Path, roots: Sequence[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        return True
    return False


def _json_path(parts: Iterable[Any]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        elif isinstance(part, str) and part.isidentifier():
            path += f".{part}"
        else:
            path += f"[{json.dumps(part, ensure_ascii=False)}]"
    return path
