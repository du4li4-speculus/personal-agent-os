"""Plain text, PDF, and common document extraction adapter."""

from __future__ import annotations

from io import BytesIO
import re
import subprocess
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from .base_adapter import (
    AdapterError,
    InputAdapter,
    make_source_record,
    read_source_bytes,
)


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rtf", ".text"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc"}


def _decode(payload: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-16", "gb18030", "latin-1"):
        try:
            return payload.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace"), "utf-8-replace"


def _strip_rtf(text: str) -> str:
    text = re.sub(r"\\'[0-9a-fA-F]{2}", "", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    return text.replace("{", "").replace("}", "")


def _docx_text(payload: bytes) -> str:
    try:
        with ZipFile(BytesIO(payload)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
    except (BadZipFile, KeyError) as exc:
        raise AdapterError(f"Unable to read DOCX XML: {exc}") from exc
    xml = re.sub(r"</w:p>|</w:tr>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return "\n".join(
        re.sub(r"[ \t]+", " ", line).strip()
        for line in xml.splitlines()
        if line.strip()
    )


def _pdf_text(payload: bytes) -> tuple[str | None, str]:
    try:
        completed = subprocess.run(
            ["pdftotext", "-layout", "-", "-"],
            input=payload,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None, "pdftotext-unavailable"
    if completed.returncode != 0:
        return None, "pdftotext-failed"
    return completed.stdout.decode("utf-8", errors="replace"), "pdftotext"


class TextAdapter(InputAdapter):
    name = "text_adapter"

    @classmethod
    def supports(cls, source: Any) -> bool:
        if isinstance(source, (bytes, bytearray)):
            return True
        if isinstance(source, Path) or isinstance(source, str):
            path = Path(source)
            return not path.exists() or path.suffix.lower() in TEXT_EXTENSIONS | DOCUMENT_EXTENSIONS
        return False

    def adapt(
        self,
        source: Any,
        *,
        source_id: str | None = None,
        sequence: int = 1,
        role: str = "unknown",
    ) -> dict[str, Any]:
        payload, path, filename = read_source_bytes(source)
        suffix = path.suffix.lower() if path else ""
        if not suffix and payload.startswith(b"%PDF"):
            suffix = ".pdf"
        elif not suffix and payload.startswith(b"PK"):
            try:
                with ZipFile(BytesIO(payload)) as archive:
                    if "word/document.xml" in archive.namelist():
                        suffix = ".docx"
            except BadZipFile:
                pass
        warnings: list[str] = []
        method = "plain-text-decode"
        encoding = None

        if suffix == ".pdf":
            text, method = _pdf_text(payload)
            if text is None:
                warnings.append("PDF text extraction unavailable; visual/OCR review is required")
                status = "pending"
                text = None
            else:
                status = "complete"
        elif suffix == ".docx":
            text = _docx_text(payload)
            status = "complete"
            method = "docx-document-xml"
        elif suffix == ".doc":
            text = None
            status = "pending"
            method = "legacy-doc-not-decoded"
            warnings.append("Legacy .doc requires an external converter; text was not invented")
        else:
            text, encoding = _decode(payload)
            if suffix == ".rtf":
                text = _strip_rtf(text)
                method = "rtf-strip"
            status = "complete"

        format_name = suffix[1:] if suffix else "text"
        kind = "document" if suffix in DOCUMENT_EXTENSIONS else "text"
        return make_source_record(
            source=source,
            payload=payload,
            kind=kind,
            format_name=format_name,
            content={"text": text, "blocks": [], "images": []},
            extraction={
                "adapter": self.name,
                "method": method,
                "status": status,
                "encoding": encoding,
                "warnings": warnings,
            },
            source_id=source_id,
            sequence=sequence,
            role=role,
            display_filename=filename if path else f"inline.{format_name}",
        )
