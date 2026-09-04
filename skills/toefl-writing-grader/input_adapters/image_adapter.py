"""Image and screenshot adapter.

The adapter records the image as evidence input and explicitly marks OCR as
pending.  It never fabricates OCR text from pixels.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .base_adapter import InputAdapter, make_source_record, read_source_bytes


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"}


def _image_format(payload: bytes) -> str | None:
    signatures = (
        (b"\x89PNG\r\n\x1a\n", "png"),
        (b"\xff\xd8\xff", "jpeg"),
        (b"GIF8", "gif"),
        (b"RIFF", "webp"),
        (b"BM", "bmp"),
        (b"II*\x00", "tiff"),
        (b"MM\x00*", "tiff"),
    )
    for signature, format_name in signatures:
        if payload.startswith(signature):
            return format_name
    return None


class ImageAdapter(InputAdapter):
    name = "image_adapter"

    @classmethod
    def supports(cls, source: Any) -> bool:
        if isinstance(source, Path):
            return source.suffix.lower() in IMAGE_EXTENSIONS
        if isinstance(source, str):
            return Path(source).suffix.lower() in IMAGE_EXTENSIONS
        return isinstance(source, (bytes, bytearray)) and _image_format(bytes(source)) is not None

    def adapt(
        self,
        source: Any,
        *,
        source_id: str | None = None,
        sequence: int = 1,
        role: str = "unknown",
    ) -> dict[str, Any]:
        payload, path, filename = read_source_bytes(source)
        digest = hashlib.sha256(payload).hexdigest()
        format_name = path.suffix.lower().lstrip(".") if path else (_image_format(payload) or "image")
        display_filename = filename if path else f"inline.{format_name}"
        return make_source_record(
            source=source,
            payload=payload,
            kind="image",
            format_name=format_name,
            content={
                "text": None,
                "blocks": [],
                "images": [
                    {
                        "asset_id": f"image-{digest[:12]}",
                        "filename": filename,
                        "uri": str(path),
                        "sha256": digest,
                        "ocr_status": "pending",
                    }
                ],
            },
            extraction={
                "adapter": self.name,
                "method": "metadata-only",
                "status": "pending_ocr",
                "warnings": ["OCR is required before prompt or response text can be assessed"],
            },
            source_id=source_id,
            sequence=sequence,
            role=role,
            display_filename=display_filename,
        )
