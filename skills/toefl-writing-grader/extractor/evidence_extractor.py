"""Convert source_bundle.json into conservative, traceable evidence.json."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping


def _evidence_id(bundle_id: str, source_id: str, suffix: str) -> str:
    return f"{bundle_id}:{source_id}:{suffix}"


def extract_evidence(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Extract only evidence present in the bundle; no scoring or completion inference."""

    bundle_id = str(bundle.get("bundle_id", "unknown-bundle"))
    items: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for source in bundle.get("sources", []):
        source_id = str(source.get("source_id", "unknown-source"))
        content = source.get("content") or {}
        extraction = source.get("extraction") or {}
        role = source.get("role", "unknown")
        text = content.get("text")
        if text:
            items.append(
                {
                    "evidence_id": _evidence_id(bundle_id, source_id, "text"),
                    "source_id": source_id,
                    "type": "prompt_text" if role == "prompt" else "response_text" if role == "response" else "unclassified_text",
                    "role": role,
                    "text": text,
                    "locator": {"uri": source.get("uri"), "sequence": source.get("sequence")},
                    "provenance": {
                        "adapter": extraction.get("adapter"),
                        "method": extraction.get("method"),
                        "confidence": 1.0,
                    },
                }
            )
        else:
            gaps.append(
                {
                    "source_id": source_id,
                    "code": "TEXT_NOT_AVAILABLE",
                    "reason": "The adapter did not produce text; OCR or a document extractor is required",
                    "status": extraction.get("status", "unknown"),
                    "blocking": True,
                }
            )

        annotations = content.get("annotations") or {}
        for index, match in enumerate(annotations.get("sentence_exercise_matches", []), start=1):
            items.append(
                {
                    "evidence_id": _evidence_id(bundle_id, source_id, f"annotation-{index}"),
                    "source_id": source_id,
                    "type": "annotation",
                    "role": "annotation",
                    "text": match.get("raw"),
                    "locator": {"uri": source.get("uri"), "sequence": source.get("sequence")},
                    "attributes": {
                        "error_count": match.get("error_count"),
                        "denominator": match.get("denominator"),
                    },
                    "provenance": {
                        "adapter": extraction.get("adapter"),
                        "method": "pages-iwa-search",
                        "confidence": 1.0,
                    },
                }
            )

        for index, image in enumerate(content.get("images") or [], start=1):
            verified_transcription = image.get("ocr_status") in {
                "complete", "verified_transcription", "visual_transcription"
            }
            items.append(
                {
                    "evidence_id": _evidence_id(bundle_id, source_id, f"image-{index}"),
                    "source_id": source_id,
                    "type": "image_reference",
                    "role": "image" if role == "unknown" else role,
                    "text": None,
                    "locator": {
                        "uri": image.get("uri") or source.get("uri"),
                        "package_member": image.get("package_member"),
                        "sequence": source.get("sequence"),
                    },
                    "provenance": {
                        "adapter": extraction.get("adapter"),
                        "method": "image-reference",
                        "confidence": 1.0,
                    },
                    "requires": ["ocr_or_visual_transcription"],
                }
            )
            if not verified_transcription:
                gaps.append(
                    {
                        "source_id": source_id,
                        "code": "IMAGE_TEXT_PENDING",
                        "reason": "Image evidence has no verified text transcription",
                        "status": "pending_ocr",
                        "blocking": not bool(text and role == "response"),
                    }
                )

        if extraction.get("warnings"):
            gaps.append(
                {
                    "source_id": source_id,
                    "code": "ADAPTER_WARNING",
                    "reason": " ; ".join(extraction["warnings"]),
                    "status": extraction.get("status", "warning"),
                    "blocking": any(
                        marker in " ; ".join(extraction["warnings"])
                        for marker in ("text extraction", "OCR", "extractor", "IWA is missing")
                    ),
                }
            )

    prompt_available = any(item.get("type") == "prompt_text" for item in items)
    response_available = any(item.get("type") == "response_text" for item in items)
    if not prompt_available:
        gaps.append(
            {
                "source_id": None,
                "code": "PROMPT_NOT_EXPLICITLY_PROVIDED",
                "reason": "No source was explicitly tagged role=prompt; do not claim prompt verification",
                "status": "needs_user_source",
                "blocking": True,
            }
        )

    return {
        "schema_version": "1.0",
        "evidence_id": f"evidence-{bundle_id}",
        "bundle_id": bundle_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "gaps": gaps,
        "summary": {
            "source_count": len(bundle.get("sources", [])),
            "evidence_count": len(items),
            "prompt_available": prompt_available,
            "response_available": response_available,
            "assessment_ready": bool(
                prompt_available
                and response_available
                and not any(gap.get("blocking", False) for gap in gaps)
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_bundle", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("evidence.json"))
    args = parser.parse_args()
    bundle = json.loads(args.source_bundle.read_text(encoding="utf-8"))
    evidence = extract_evidence(bundle)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
