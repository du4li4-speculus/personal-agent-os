from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

import yaml

from runtime.contract_validator import ContractValidator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY_ROOT / "skills" / "toefl-writing-grader"
SOURCE_SCHEMA = SKILL_ROOT / "schemas" / "source_bundle.schema.json"
EVIDENCE_SCHEMA = SKILL_ROOT / "schemas" / "evidence.schema.json"


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    + _png_chunk("IHDR".encode(), struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    + _png_chunk("IDAT".encode(), zlib.compress(b"\x00\x00\x00\x00\x00"))
    + _png_chunk("IEND".encode(), b"")
)


def _load_skill_package(module_name: str, package_dir: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        module_name,
        package_dir / "__init__.py",
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load TOEFL package: {package_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


INPUT_ADAPTERS = _load_skill_package(
    "_toefl_input_adapters", SKILL_ROOT / "input_adapters"
)
EXTRACTOR = _load_skill_package("_toefl_extractor", SKILL_ROOT / "extractor")
normalize_sources = INPUT_ADAPTERS.normalize_sources
extract_evidence = EXTRACTOR.extract_evidence


def gap_codes(evidence: Mapping[str, Any]) -> set[str]:
    return {str(gap["code"]) for gap in evidence["gaps"]}


def evidence_from_image_fixture() -> dict[str, Any]:
    bundle = normalize_sources([MINIMAL_PNG], roles=["prompt"])
    return extract_evidence(bundle)


class TOEFLInputEvidenceTestCase(unittest.TestCase):
    def assertSchemaValid(
        self, document: Mapping[str, Any], schema_path: Path
    ) -> None:
        violations = ContractValidator(REPOSITORY_ROOT).validate(
            document, schema_path
        )
        self.assertEqual(violations, ())

    def test_text_adapter_preserves_provenance_without_domain_inference(self) -> None:
        response = "A student response with only source-grounded text."
        bundle = normalize_sources([response], roles=["response"])
        evidence = extract_evidence(bundle)
        source = bundle["sources"][0]
        item = evidence["items"][0]

        self.assertEqual(source["role"], "response")
        self.assertEqual(source["sha256"], hashlib.sha256(response.encode()).hexdigest())
        self.assertEqual(source["extraction"]["adapter"], "text_adapter")
        self.assertIsNone(source["uri"])
        self.assertEqual(item["source_id"], source["source_id"])
        self.assertEqual(item["provenance"]["adapter"], "text_adapter")
        serialized = json.dumps(
            {"bundle": bundle, "evidence": evidence}, ensure_ascii=False
        ).lower()
        for forbidden in ("score", "rubric", "diagnosis", "learning_recommendation"):
            self.assertNotIn(forbidden, serialized)

    def test_assessment_is_blocked_without_explicit_prompt(self) -> None:
        bundle = normalize_sources(["student text"], roles=["response"])
        evidence = extract_evidence(bundle)

        self.assertFalse(evidence["summary"]["prompt_available"])
        self.assertTrue(evidence["summary"]["response_available"])
        self.assertFalse(evidence["summary"]["assessment_ready"])
        self.assertIn("PROMPT_NOT_EXPLICITLY_PROVIDED", gap_codes(evidence))

    def test_explicit_prompt_and_response_are_assessment_ready(self) -> None:
        bundle = normalize_sources(
            ["What is your position?", "My position is supported by one example."],
            roles=["prompt", "response"],
        )
        evidence = extract_evidence(bundle)

        self.assertTrue(evidence["summary"]["prompt_available"])
        self.assertTrue(evidence["summary"]["response_available"])
        self.assertTrue(evidence["summary"]["assessment_ready"])
        self.assertEqual(evidence["gaps"], [])

    def test_image_input_preserves_pending_ocr_without_fake_location(self) -> None:
        bundle = normalize_sources([MINIMAL_PNG], roles=["prompt"])
        evidence = extract_evidence(bundle)
        source = bundle["sources"][0]
        image = source["content"]["images"][0]
        image_item = next(
            item for item in evidence["items"] if item["type"] == "image_reference"
        )

        self.assertEqual(source["extraction"]["status"], "pending_ocr")
        self.assertIsNone(source["content"]["text"])
        self.assertIsNone(image["uri"])
        self.assertIsNone(image_item["text"])
        self.assertIsNone(image_item["locator"]["uri"])
        self.assertIn("IMAGE_TEXT_PENDING", gap_codes(evidence))
        self.assertFalse(evidence["summary"]["assessment_ready"])

    def test_unresolved_document_preserves_pending_and_blocking_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "unresolved.doc"
            document.write_bytes(b"legacy document bytes without extracted text")
            bundle = normalize_sources([document], roles=["response"])
        evidence = extract_evidence(bundle)
        source = bundle["sources"][0]

        self.assertEqual(source["kind"], "document")
        self.assertEqual(source["extraction"]["status"], "pending")
        self.assertIsNone(source["content"]["text"])
        self.assertIn("TEXT_NOT_AVAILABLE", gap_codes(evidence))
        self.assertTrue(any(gap.get("blocking") for gap in evidence["gaps"]))
        self.assertFalse(evidence["summary"]["assessment_ready"])

    def test_generated_source_and_evidence_documents_are_schema_valid(self) -> None:
        bundles = (
            normalize_sources(
                ["Explicit prompt", "Explicit response"],
                roles=["prompt", "response"],
            ),
            normalize_sources([MINIMAL_PNG], roles=["prompt"]),
        )
        for bundle in bundles:
            evidence = extract_evidence(bundle)
            self.assertSchemaValid(bundle, SOURCE_SCHEMA)
            self.assertSchemaValid(evidence, EVIDENCE_SCHEMA)

    def test_image_fixture_exposes_explicit_pending_gap(self) -> None:
        evidence = evidence_from_image_fixture()

        self.assertIn("IMAGE_TEXT_PENDING", gap_codes(evidence))

    def test_composite_skill_remains_development_without_entrypoint(self) -> None:
        registry = yaml.safe_load(
            (REPOSITORY_ROOT / "registry" / "skill_registry.yaml").read_text(
                encoding="utf-8"
            )
        )
        manifest = yaml.safe_load(
            (SKILL_ROOT / "manifest.yaml").read_text(encoding="utf-8")
        )

        self.assertEqual(
            registry["skills"]["toefl-writing-grader"]["status"], "development"
        )
        self.assertNotIn("entrypoint", manifest)


if __name__ == "__main__":
    unittest.main()
