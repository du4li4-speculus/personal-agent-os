"""Apple Pages package adapter with conservative IWA text and annotation checks."""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any
from zipfile import BadZipFile, ZipFile, is_zipfile

from .base_adapter import AdapterError, InputAdapter, make_source_record, read_source_bytes


def _read_varint(payload: bytes, index: int = 0) -> tuple[int, int]:
    value = 0
    shift = 0
    while index < len(payload) and shift <= 63:
        byte = payload[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, index
        shift += 7
    raise ValueError("invalid Snappy varint")


def _snappy_raw_decompress(payload: bytes) -> bytes:
    """Small dependency-free decoder for the raw Snappy stream used by IWA."""

    expected, index = _read_varint(payload)
    output = bytearray()
    while len(output) < expected:
        if index >= len(payload):
            raise ValueError("truncated Snappy tag")
        tag = payload[index]
        index += 1
        tag_type = tag & 0x03
        if tag_type == 0:
            length_code = tag >> 2
            if length_code < 60:
                length = length_code + 1
            else:
                extra = length_code - 59
                if index + extra > len(payload):
                    raise ValueError("truncated Snappy literal length")
                length = int.from_bytes(payload[index:index + extra], "little") + 1
                index += extra
            if index + length > len(payload):
                raise ValueError("truncated Snappy literal")
            output.extend(payload[index:index + length])
            index += length
            continue

        if tag_type == 1:
            length = ((tag >> 2) & 0x07) + 4
            if index + 1 > len(payload):
                raise ValueError("truncated Snappy short copy")
            offset = ((tag & 0xE0) << 3) | payload[index]
            index += 1
        elif tag_type == 2:
            length = (tag >> 2) + 1
            if index + 2 > len(payload):
                raise ValueError("truncated Snappy copy")
            offset = int.from_bytes(payload[index:index + 2], "little")
            index += 2
        else:
            length = (tag >> 2) + 1
            if index + 4 > len(payload):
                raise ValueError("truncated Snappy long copy")
            offset = int.from_bytes(payload[index:index + 4], "little")
            index += 4
        if offset <= 0 or offset > len(output):
            raise ValueError("invalid Snappy copy offset")
        for _ in range(length):
            output.append(output[-offset])

    if len(output) != expected:
        raise ValueError("Snappy output length mismatch")
    return bytes(output)


def _decompress_iwa(payload: bytes) -> bytes:
    """Try the established IWA offsets, then keep raw bytes for safe fallback."""

    try:
        import snappy  # type: ignore

        for offset in (4, 0, 8):
            try:
                return snappy.decompress(payload[offset:])
            except Exception:
                pass
    except ImportError:
        pass
    for offset in (4, 0, 8):
        try:
            return _snappy_raw_decompress(payload[offset:])
        except Exception:
            pass
    return payload


def _visible_fragments(payload: bytes) -> list[str]:
    """Extract body-like runs while excluding obvious IWA metadata noise."""

    fragments: list[str] = []
    decoded = payload.decode("utf-8", errors="ignore")
    fragments.extend(
        re.findall(
            r"[\u3400-\u9fff\uf900-\ufaff]+|[A-Za-z][A-Za-z0-9 ,.'!?;:/()\-]{2,}",
            decoded,
        )
    )
    fragments.extend(
        match.decode("ascii", errors="ignore")
        for match in re.findall(rb"[\x20-\x7e]{2,}", payload)
    )
    result: list[str] = []
    metadata_noise = {
        "CN", "CNP", "gregorian", "latn", "一月", "二月", "三月", "四月", "五月", "六月",
        "七月", "八月", "九月", "十月", "十一月", "十二月", "星期日", "星期一", "星期二",
        "星期三", "星期四", "星期五", "星期六", "第一季度", "第二季度", "第三季度",
        "第四季度", "公元前", "公元", "上午", "下午", "季度", "NaN", "CNY", "AUD", "BRL",
        "CAD", "EUR", "GBP", "HKD", "ILR", "ILS", "INR", "JPY", "KRW", "MXN", "NZD",
        "TWD", "USD", "VND", "XAF", "XCD", "XCG", "XOF", "XPF",
    }
    seen: set[str] = set()
    for fragment in fragments:
        value = re.sub(r"\s+", " ", fragment).strip()
        words = re.findall(r"[A-Za-z]{2,}", value)
        common_words = set(words) & {
            "a", "about", "and", "are", "because", "can", "could", "for",
            "from", "have", "how", "i", "in", "is", "it", "my", "of",
            "on", "please", "that", "the", "this", "to", "we", "what",
            "when", "which", "with", "would", "you",
        }
        body_like = (
            len(words) >= 8
            or (value.lower().startswith(("dear ", "best regards", "sincerely")) and len(words) >= 3)
            or (len(words) >= 4 and len(common_words) >= 2)
        )
        chinese_like = bool(re.search(r"[\u3400-\u9fff\uf900-\ufaff]", value)) and len(value) >= 3
        if (
            value
            and value not in seen
            and value not in metadata_noise
            and not value.startswith("造句")
            and (body_like or chinese_like)
        ):
            seen.add(value)
            result.append(value)
    return result


def _searchable_iwa_text(payload: bytes) -> str:
    """Return decoded text for keyword checks, including short Chinese labels."""

    decoded = _decompress_iwa(payload).decode("utf-8", errors="ignore")
    return re.sub(r"[\x00-\x1f\ufffc]+", "\n", decoded)


def _sentence_matches(text: str) -> list[dict[str, Any]]:
    matches = []
    exact_pattern = re.compile(r"造句\s*[:：]?\s*错\s*(\d+)\s*/\s*10")
    broad_pattern = re.compile(r"造句[^\n]{0,30}")
    seen: set[str] = set()
    for match in broad_pattern.finditer(text):
        exact = exact_pattern.search(match.group(0))
        raw = re.sub(r"\s+", " ", match.group(0)).strip()
        if raw in seen:
            continue
        seen.add(raw)
        matches.append(
            {
                "raw": raw,
                "error_count": int(exact.group(1)) if exact else None,
                "denominator": 10 if exact else None,
            }
        )
    return matches


class PagesAdapter(InputAdapter):
    name = "pages_adapter"

    @classmethod
    def supports(cls, source: Any) -> bool:
        if isinstance(source, str):
            return source.lower().endswith(".pages")
        if isinstance(source, (bytes, bytearray)):
            try:
                with ZipFile(BytesIO(bytes(source))) as archive:
                    return "Index/Document.iwa" in archive.namelist()
            except BadZipFile:
                return False
        return getattr(source, "suffix", "").lower() == ".pages"

    def adapt(
        self,
        source: Any,
        *,
        source_id: str | None = None,
        sequence: int = 1,
        role: str = "unknown",
    ) -> dict[str, Any]:
        payload, path, _ = read_source_bytes(source)
        if not is_zipfile(BytesIO(payload)):
            raise AdapterError(".pages input is not a readable package")

        try:
            with ZipFile(BytesIO(payload)) as archive:
                names = archive.namelist()
                document_payload = archive.read("Index/Document.iwa") if "Index/Document.iwa" in names else b""
                metadata_payload = archive.read("Index/Metadata.iwa") if "Index/Metadata.iwa" in names else b""
                annotation_name = "Index/AnnotationAuthorStorage-1732609.iwa"
                annotation_payload = archive.read(annotation_name) if annotation_name in names else b""
                all_iwa_payloads = [archive.read(name) for name in names if name.endswith(".iwa")]
                image_names = [name for name in names if name.startswith("Data/")]
        except (BadZipFile, KeyError) as exc:
            raise AdapterError(f"Unable to read Pages package: {exc}") from exc

        document_text = _decompress_iwa(document_payload)
        metadata_text = _decompress_iwa(metadata_payload)
        fragments = _visible_fragments(document_text)
        metadata_fragments = _visible_fragments(metadata_text)
        extracted_text = "\n".join(fragments)
        annotation_text = "\n".join(_searchable_iwa_text(payload_item) for payload_item in all_iwa_payloads)
        searchable_text = "\n".join(
            [_searchable_iwa_text(document_payload), _searchable_iwa_text(metadata_payload), annotation_text]
        )
        sentence_matches = _sentence_matches(searchable_text)
        annotation_storage_present = annotation_name in names
        annotation_fragments = _visible_fragments(_decompress_iwa(annotation_payload))
        annotation_storage_nonempty = bool(
            annotation_fragments
            or re.search(r"造句|错\s*\d+|全对", _searchable_iwa_text(annotation_payload))
        )
        warnings = []
        if not document_payload:
            warnings.append("Index/Document.iwa is missing; text extraction is incomplete")
        if not fragments:
            warnings.append("No readable text run was extracted from IWA; inspect embedded images/OCR")
        if not annotation_storage_nonempty:
            warnings.append("Annotation storage is absent or empty; this is not proof that no annotations exist")

        images = [
            {"asset_id": f"pages-image-{index}", "package_member": name, "ocr_status": "pending"}
            for index, name in enumerate(image_names, start=1)
        ]
        return make_source_record(
            source=source,
            payload=payload,
            kind="pages",
            format_name="pages",
            content={
                "text": extracted_text or None,
                "blocks": [{"type": "text_fragment", "text": fragment} for fragment in fragments],
                "images": images,
                "annotations": {
                    "storage_present": annotation_storage_present,
                    "storage_nonempty": annotation_storage_nonempty,
                    "sentence_exercise_matches": sentence_matches,
                    "absence_is_not_proof": True,
                },
            },
            extraction={
                "adapter": self.name,
                "method": "pages-iwa-visible-runs",
                "status": "complete" if fragments and not image_names else "partial",
                "document_iwa_checked_at_start": True,
                "package_members": len(names),
                "warnings": warnings,
            },
            source_id=source_id,
            sequence=sequence,
            role=role,
            display_filename=path.name if path else "inline.pages",
        )
