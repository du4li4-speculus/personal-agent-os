"""Create isolated run directories and stage external inputs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .models import AgentRuntimeError, InputRef, RunPaths


PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_SUFFIX_PATTERN = re.compile(r"^\.[a-z0-9]{1,10}$")


class RunStore:
    """Own the physical ``<run-root>/<project-id>/<run-id>`` boundary."""

    def __init__(self, run_root: Path) -> None:
        self.run_root = Path(run_root).resolve()

    def create(self, project_id: str, run_id: str) -> RunPaths:
        _require_identifier(project_id, PROJECT_ID_PATTERN, "PROJECT_ID_INVALID")
        _require_identifier(run_id, RUN_ID_PATTERN, "RUN_ID_INVALID")
        root = (self.run_root / project_id / run_id).resolve()
        _require_within(root, self.run_root, "RUN_PATH_ESCAPE")
        if root.exists():
            raise AgentRuntimeError(
                f"Run directory already exists: {root}", code="RUN_ALREADY_EXISTS"
            )
        try:
            root.mkdir(parents=True, exist_ok=False)
            paths = RunPaths(
                root=root,
                input_dir=root / "input",
                work_dir=root / "work",
                artifact_dir=root / "artifacts",
                trace_dir=root / "trace",
                memory_dir=root / "memory",
            )
            for path in (
                paths.input_dir,
                paths.work_dir,
                paths.artifact_dir,
                paths.trace_dir,
                paths.memory_dir,
            ):
                _require_within(path.resolve(), root, "RUN_PATH_ESCAPE")
                path.mkdir()
        except OSError as exc:
            raise AgentRuntimeError(
                f"Unable to create run directory: {root}", code="RUN_CREATE_FAILED"
            ) from exc
        return paths

    def stage_inputs(
        self, paths: RunPaths, inputs: Sequence[InputRef]
    ) -> tuple[InputRef, ...]:
        self._validate_paths(paths)
        staged: list[InputRef] = []
        manifest_entries: list[dict[str, Any]] = []
        for index, input_ref in enumerate(inputs, start=1):
            source = Path(input_ref.path).resolve()
            if not source.is_file():
                raise AgentRuntimeError(
                    f"Input path does not exist or is not a file: {source}",
                    code="INPUT_NOT_FOUND",
                )
            try:
                source.relative_to(paths.root.resolve())
            except ValueError:
                pass
            else:
                raise AgentRuntimeError(
                    f"Input is already inside the new run boundary: {source}",
                    code="INPUT_SOURCE_INVALID",
                )
            if not isinstance(input_ref.role, str) or not input_ref.role.strip():
                raise AgentRuntimeError(
                    "Input role must be a non-empty string", code="INPUT_ROLE_INVALID"
                )

            suffix = source.suffix.lower()
            if not SAFE_SUFFIX_PATTERN.fullmatch(suffix):
                suffix = ""
            destination = paths.input_dir / f"input-{index:04d}{suffix}"
            _require_within(destination.resolve(), paths.input_dir, "INPUT_PATH_ESCAPE")
            try:
                shutil.copyfile(source, destination)
            except OSError as exc:
                raise AgentRuntimeError(
                    f"Unable to stage input: {source}", code="INPUT_STAGE_FAILED"
                ) from exc
            digest = _sha256(destination)
            staged_ref = InputRef(
                path=destination.resolve(),
                role=input_ref.role,
                media_type=input_ref.media_type,
            )
            staged.append(staged_ref)
            manifest_entries.append(
                {
                    "path": destination.relative_to(paths.root).as_posix(),
                    "role": input_ref.role,
                    "media_type": input_ref.media_type,
                    "sha256": digest,
                    "byte_size": destination.stat().st_size,
                }
            )

        _write_json_atomic(
            paths.input_dir / "manifest.json",
            {"schema_version": "1.0", "inputs": manifest_entries},
        )
        return tuple(staged)

    def _validate_paths(self, paths: RunPaths) -> None:
        _require_within(paths.root.resolve(), self.run_root, "RUN_PATH_ESCAPE")
        for path in (
            paths.input_dir,
            paths.work_dir,
            paths.artifact_dir,
            paths.trace_dir,
            paths.memory_dir,
        ):
            _require_within(path.resolve(), paths.root.resolve(), "RUN_PATH_ESCAPE")
            if not path.is_dir():
                raise AgentRuntimeError(
                    f"Run directory is missing: {path}", code="RUN_PATH_MISSING"
                )


def _require_identifier(value: str, pattern: re.Pattern[str], code: str) -> None:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise AgentRuntimeError(f"{code}: {value!r}", code=code)


def _require_within(path: Path, root: Path, code: str) -> None:
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise AgentRuntimeError(f"{code}: {path}", code=code) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
