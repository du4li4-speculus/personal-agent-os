"""Common contracts for normalising TOEFL writing inputs.

Adapters preserve provenance and never infer a prompt, student name, score, or
missing text.  They are deliberately dependency-light so the evidence layer
can run before any assessment implementation is selected.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import mimetypes
from pathlib import Path
from typing import Any, Mapping


class AdapterError(ValueError):
    """Raised when an input cannot be handled by an adapter."""


def _as_path(source: Any) -> Path | None:
    if isinstance(source, Path):
        try:
            return source if source.exists() else None
        except OSError:
            return None
    if isinstance(source, str):
        candidate = Path(source)
        try:
            return candidate if candidate.exists() and candidate.is_file() else None
        except OSError:
            # Long inline text is not a filesystem path.  Treat it as text
            # instead of allowing Path.stat() to abort the adapter chain.
            return None
    return None


def read_source_bytes(source: Any) -> tuple[bytes, Path | None, str]:
    """Return bytes, optional local path, and a safe display filename."""

    path = _as_path(source)
    if path is not None:
        return path.read_bytes(), path, path.name
    if isinstance(source, bytes):
        return source, None, "inline-source"
    if isinstance(source, bytearray):
        return bytes(source), None, "inline-source"
    if isinstance(source, str):
        return source.encode("utf-8"), None, "inline-text.txt"
    raise AdapterError(f"Unsupported input value: {type(source).__name__}")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def mime_for(filename: str, format_name: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    return {
        "text": "text/plain",
        "document": "application/octet-stream",
        "pages": "application/vnd.apple.pages",
        "image": "application/octet-stream",
    }.get(format_name, "application/octet-stream")


def make_source_record(
    *,
    source: Any,
    payload: bytes,
    kind: str,
    format_name: str,
    content: Mapping[str, Any],
    extraction: Mapping[str, Any],
    source_id: str | None = None,
    sequence: int = 1,
    role: str = "unknown",
    display_filename: str | None = None,
) -> dict[str, Any]:
    """Build one source record with stable identity and explicit provenance."""

    path = _as_path(source)
    filename = display_filename or (path.name if path else ("inline-text.txt" if kind == "text" else "inline-source"))
    digest = sha256_bytes(payload)
    return {
        "source_id": source_id or f"source-{digest[:12]}",
        "sequence": sequence,
        "role": role,
        "kind": kind,
        "format": format_name,
        "filename": filename,
        "uri": str(path) if path else None,
        "mime_type": mime_for(filename, format_name),
        "sha256": digest,
        "byte_size": len(payload),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "content": dict(content),
        "extraction": dict(extraction),
    }


class InputAdapter(ABC):
    """Adapter interface used by the input layer."""

    name: str

    @classmethod
    @abstractmethod
    def supports(cls, source: Any) -> bool:
        """Whether this adapter can accept the source."""

    @abstractmethod
    def adapt(
        self,
        source: Any,
        *,
        source_id: str | None = None,
        sequence: int = 1,
        role: str = "unknown",
    ) -> dict[str, Any]:
        """Return one source record conforming to source_bundle.schema.json."""


def build_source_bundle(
    records: list[Mapping[str, Any]], *, bundle_id: str | None = None
) -> dict[str, Any]:
    """Wrap adapter records into the unified source_bundle.json shape."""

    if not records:
        raise AdapterError("A source bundle must contain at least one source")
    return {
        "schema_version": "1.0",
        "bundle_id": bundle_id or f"bundle-{sha256_bytes(str(records).encode())[:12]}",
        "sources": [dict(record) for record in records],
        "metadata": {
            "adapter_count": len(records),
            "prompt_sources_explicit": sum(
                1 for record in records if record.get("role") == "prompt"
            ),
            "response_sources_explicit": sum(
                1 for record in records if record.get("role") == "response"
            ),
        },
    }


def normalize_sources(
    sources: list[Any],
    *,
    roles: list[str] | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Route mixed inputs through adapters and optionally write source_bundle.json."""

    if not sources:
        raise AdapterError("At least one input source is required")
    # Local imports keep the base contract independent from concrete adapters.
    from .image_adapter import ImageAdapter
    from .pages_adapter import PagesAdapter
    from .text_adapter import TextAdapter

    adapters = (PagesAdapter(), ImageAdapter(), TextAdapter())
    records = []
    roles = roles or ["unknown"] * len(sources)
    if len(roles) != len(sources):
        raise AdapterError("roles must have the same length as sources")
    for sequence, (source, role) in enumerate(zip(sources, roles), start=1):
        for adapter in adapters:
            if adapter.supports(source):
                records.append(adapter.adapt(source, sequence=sequence, role=role))
                break
        else:
            raise AdapterError(f"No input adapter supports source {source!r}")

    bundle = build_source_bundle(records)
    if output_path is not None:
        import json

        Path(output_path).write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return bundle
