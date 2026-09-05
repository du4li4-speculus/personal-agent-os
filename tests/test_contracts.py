from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

import yaml

from runtime.contract_validator import ContractValidator
from runtime.models import AgentRuntimeError, ContractError
from runtime.registry_loader import RegistryLoader
from runtime.skill_loader import SkillLoader


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"


def registry_document(
    *, status: str = "development", version: str = "1.0.0"
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "skills": {
            "sample": {
                "version": version,
                "status": status,
                "path": "skills/sample",
                "manifest": "manifest.yaml",
            }
        },
    }


def manifest_document(
    *, entrypoint: Mapping[str, str] | None = None, version: str = "1.0.0"
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "1.0",
        "name": "sample",
        "version": version,
        "kind": "workflow",
        "inputs": {
            "contract": "schemas/input.schema.json",
            "accepted_formats": ["text"],
        },
        "intermediate_outputs": [],
        "outputs": [{"name": "result", "path": "result.txt"}],
        "capabilities": {
            "required": ["runtime.execution_proof", "runtime.validation"],
            "optional": [],
        },
        "cognition": {
            "mode": "optional",
            "prepare": ["decision"],
            "critique": ["critique"],
            "memory_review": "memory",
        },
    }
    if entrypoint is not None:
        document["entrypoint"] = dict(entrypoint)
    return document


def project_document(**overrides: Any) -> dict[str, Any]:
    document = {
        "schema_version": "1.0",
        "project_id": "sample-project",
        "allowed_skills": ["sample"],
        "cognition_mode": "optional",
        "memory_policy": "candidate_only",
    }
    document.update(overrides)
    return document


def run_record_document(**overrides: Any) -> dict[str, Any]:
    document = {
        "schema_version": "1.0",
        "run_id": "run-identifier",
        "project_id": "sample-project",
        "skill_name": "sample",
        "skill_version": "1.0.0",
        "state": "CREATED",
        "input_refs": [],
        "artifact_refs": [],
        "trace_ref": "trace/execution_trace.json",
    }
    document.update(overrides)
    return document


def memory_candidate_document(**overrides: Any) -> dict[str, Any]:
    document = {
        "schema_version": "1.0",
        "candidate_id": "candidate-identifier",
        "project_id": "sample-project",
        "run_id": "run-identifier",
        "scope": "project",
        "target_id": "sample-project",
        "proposition": "Evidence-backed reusable lesson",
        "evidence_refs": ["trace/execution_trace.json"],
        "status": "proposed",
    }
    document.update(overrides)
    return document


def agent_role_document(**overrides: Any) -> dict[str, Any]:
    document = {
        "schema_version": "1.0",
        "name": "architecture-reviewer",
        "objective": "Evaluate one architecture decision",
        "responsibility": "Return a bounded review",
        "inputs": ["decision_record"],
        "outputs": ["review_result"],
        "constraints": ["no_domain_knowledge_storage"],
        "evaluation_criteria": ["findings_are_evidence_linked"],
        "why_agent_required": "Independent lifecycle and evaluation are required",
        "why_skill_insufficient": (
            "The role coordinates multiple Skills and owns no domain capability"
        ),
    }
    document.update(overrides)
    return document


def _write_contract_repository(
    root: Path, registry: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    shutil.copytree(CONTRACTS_ROOT, root / "contracts")
    registry_dir = root / "registry"
    skill_dir = root / "skills" / "sample"
    schema_dir = skill_dir / "schemas"
    source_dir = skill_dir / "src"
    registry_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    (registry_dir / "skill_registry.yaml").write_text(
        yaml.safe_dump(dict(registry), sort_keys=False), encoding="utf-8"
    )
    (skill_dir / "manifest.yaml").write_text(
        yaml.safe_dump(dict(manifest), sort_keys=False), encoding="utf-8"
    )
    (skill_dir / "SKILL.md").write_text("# Sample\n", encoding="utf-8")
    (schema_dir / "input.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
        encoding="utf-8",
    )
    (source_dir / "sample_entry.py").write_text(
        "def execute(context):\n    return {}\n", encoding="utf-8"
    )


def validate_registry_manifest_pair(
    registry: Mapping[str, Any], manifest: Mapping[str, Any]
) -> tuple[str, ...]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_contract_repository(root, registry, manifest)
        try:
            SkillLoader(RegistryLoader(root)).load_registered("sample")
        except AgentRuntimeError as exc:
            return (exc.code,)
    return ()


def validate_pair(
    *, registry_version: str, manifest_version: str
) -> tuple[str, ...]:
    return validate_registry_manifest_pair(
        registry_document(version=registry_version),
        manifest_document(version=manifest_version),
    )


class ContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = ContractValidator(REPOSITORY_ROOT)

    def assertSchemaError(
        self,
        document: Mapping[str, Any],
        schema_name: str,
        keyword: str,
        path: str,
    ) -> None:
        errors = self.validator.validate(document, CONTRACTS_ROOT / schema_name)
        self.assertTrue(errors, f"expected {keyword!r} error at {path!r}")
        self.assertIn((keyword, path), {(error.keyword, error.path) for error in errors})

    def test_complete_factory_documents_match_all_six_contracts(self) -> None:
        documents = (
            (registry_document(), "skill-registry.schema.json"),
            (manifest_document(), "skill-manifest.schema.json"),
            (project_document(), "project.schema.json"),
            (run_record_document(), "run-record.schema.json"),
            (memory_candidate_document(), "memory-candidate.schema.json"),
            (agent_role_document(), "agent-role.schema.json"),
        )
        for document, schema_name in documents:
            with self.subTest(schema=schema_name):
                self.assertEqual(
                    self.validator.validate(document, CONTRACTS_ROOT / schema_name), ()
                )

    def test_active_skill_requires_entrypoint(self) -> None:
        errors = validate_registry_manifest_pair(
            registry_document(status="active"), manifest_document(entrypoint=None)
        )
        self.assertIn("ACTIVE_SKILL_ENTRYPOINT_MISSING", errors)

    def test_registry_and_manifest_versions_must_match(self) -> None:
        errors = validate_pair(
            registry_version="1.0.0", manifest_version="2.0.0"
        )
        self.assertIn("SKILL_VERSION_MISMATCH", errors)

    def test_agent_role_requires_skill_insufficiency_rationale(self) -> None:
        document = agent_role_document(why_skill_insufficient="")
        self.assertSchemaError(
            document,
            "agent-role.schema.json",
            "minLength",
            "$.why_skill_insufficient",
        )

    def test_memory_candidate_cannot_claim_promotion(self) -> None:
        document = memory_candidate_document(status="promoted")
        self.assertSchemaError(
            document, "memory-candidate.schema.json", "enum", "$.status"
        )

    def test_project_cannot_redefine_skill_semantics(self) -> None:
        document = project_document(skill_semantics={"sample": "overridden"})
        self.assertSchemaError(
            document, "project.schema.json", "additionalProperties", "$"
        )

    def test_schema_path_must_stay_inside_an_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "outside.schema.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaises(ContractError) as raised:
                self.validator.validate({}, outside)
        self.assertEqual(raised.exception.code, "CONTRACT_SCHEMA_PATH_ESCAPE")

    def test_live_toefl_contract_is_valid_but_not_active(self) -> None:
        registry = RegistryLoader(REPOSITORY_ROOT)
        entry = registry.get_registered("toefl-writing-grader")
        skill = SkillLoader(registry).load_registered("toefl-writing-grader")
        self.assertEqual(entry.status, "development")
        self.assertIsNone(skill.contract.entrypoint)
        with self.assertRaises(AgentRuntimeError) as raised:
            registry.get("toefl-writing-grader")
        self.assertEqual(raised.exception.code, "SKILL_NOT_ACTIVE")


if __name__ == "__main__":
    unittest.main()
