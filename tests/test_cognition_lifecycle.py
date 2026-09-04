from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

import yaml

from runtime.capabilities import CapabilitySet
from runtime.cognition_manager import CognitionManager
from runtime.contract_validator import ContractValidator
from runtime.models import CapabilityProvider, RunResult, ValidationResult
from runtime.runner import AgentRuntime
from runtime.validator_engine import ValidatorEngine
from tests.test_runtime import write_active_sample_repository


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _configure_fixture(
    root: Path, *, skill_mode: str, project_mode: str
) -> None:
    write_active_sample_repository(root)

    manifest_path = root / "skills" / "sample" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["cognition"]["mode"] = skill_mode
    if "cognition.execute" not in manifest["capabilities"]["optional"]:
        manifest["capabilities"]["optional"].append("cognition.execute")
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )

    project_path = root / "projects" / "test" / "project.yaml"
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project["cognition_mode"] = project_mode
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")


def _read_trace(result: RunResult) -> dict[str, Any]:
    if result.trace_path is None:
        raise AssertionError(f"Run did not persist a trace: {result.to_dict()}")
    return json.loads(result.trace_path.read_text(encoding="utf-8"))


def run_without_cognition_provider(
    temp_root: Path,
    *,
    skill_mode: str = "optional",
    project_mode: str = "optional",
) -> tuple[RunResult, dict[str, Any], Path]:
    repository = temp_root / "repository"
    _configure_fixture(
        repository, skill_mode=skill_mode, project_mode=project_mode
    )
    result = AgentRuntime(repository).run(
        task="exercise cognition lifecycle",
        skill_name="sample",
        project_id="test",
        inputs=(),
        run_root=temp_root / "runs",
        capabilities={},
    )
    return result, _read_trace(result), repository


class CognitionLifecycleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_root = Path(self.temp_dir.name)
        self._run_number = 0

    def _next_root(self) -> Path:
        self._run_number += 1
        return self.temp_root / f"case-{self._run_number}"

    def _run_with_provider(
        self,
        provider: CapabilityProvider,
        *,
        skill_mode: str = "optional",
        project_mode: str = "optional",
    ) -> tuple[RunResult, dict[str, Any], Path]:
        root = self._next_root()
        repository = root / "repository"
        _configure_fixture(
            repository, skill_mode=skill_mode, project_mode=project_mode
        )
        result = AgentRuntime(repository).run(
            task="exercise cognition provider",
            skill_name="sample",
            project_id="test",
            inputs=(),
            run_root=root / "runs",
            capabilities={"cognition.execute": provider},
        )
        return result, _read_trace(result), repository

    def assertPhase(
        self, trace: Mapping[str, Any], phase: str, expected_status: str
    ) -> Mapping[str, Any]:
        matches = [item for item in trace["cognition"] if item["phase"] == phase]
        self.assertEqual(len(matches), 1, trace["cognition"])
        self.assertEqual(matches[0]["status"], expected_status)
        return matches[0]

    def test_optional_cognition_is_visible_as_skipped(self) -> None:
        result, trace, _ = run_without_cognition_provider(self._next_root())
        self.assertTrue(result.succeeded, result.to_dict())
        for phase in (
            "COGNITION_PREPARE",
            "COGNITION_CRITIQUE",
            "MEMORY_REVIEW",
        ):
            record = self.assertPhase(trace, phase, "skipped")
            self.assertTrue(record["loaded"])
            self.assertFalse(record["executed"])
            self.assertFalse(record["validated"])
            self.assertFalse(record["changed_run_disposition"])
            self.assertEqual(record["reason"], "provider_unavailable")

    def test_protocol_registry_contract_and_registered_files_are_valid(self) -> None:
        document = yaml.safe_load(
            (REPOSITORY_ROOT / "cognition" / "protocol_registry.yaml").read_text(
                encoding="utf-8"
            )
        )
        violations = ContractValidator(REPOSITORY_ROOT).validate(
            document,
            REPOSITORY_ROOT
            / "contracts"
            / "cognition-protocol-registry.schema.json",
        )
        self.assertEqual(violations, ())
        manager = CognitionManager(
            REPOSITORY_ROOT, CapabilitySet({}), provider_declared=False
        )
        self.assertEqual(
            manager.validate_registry(),
            ("expansion", "decision", "critique", "memory"),
        )

    def test_protocol_symlink_escape_fails_before_domain_execution(self) -> None:
        root = self._next_root()
        repository = root / "repository"
        _configure_fixture(
            repository, skill_mode="optional", project_mode="optional"
        )
        outside = root / "outside-protocol.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        decision = repository / "cognition" / "decision_protocol.md"
        decision.unlink()
        decision.symlink_to(outside)
        result = AgentRuntime(repository).run(
            task="reject escaped cognition protocol",
            skill_name="sample",
            project_id="test",
            inputs=(),
            run_root=root / "runs",
            capabilities={},
        )
        trace = _read_trace(result)
        self.assertIn("COGNITION_PROTOCOL_INVALID", result.validation_errors[0])
        self.assertPhase(trace, "COGNITION_PREPARE", "blocked")
        self.assertEqual(list((root / "runs").rglob("execution-started.txt")), [])

    def test_required_cognition_fails_without_provider_before_execute(self) -> None:
        result, trace, repository = run_without_cognition_provider(
            self._next_root(), skill_mode="required", project_mode="disabled"
        )
        self.assertIn("COGNITION_PROVIDER_MISSING", result.validation_errors[0])
        record = self.assertPhase(trace, "COGNITION_PREPARE", "blocked")
        self.assertTrue(record["loaded"])
        self.assertFalse(record["executed"])
        self.assertTrue(record["changed_run_disposition"])
        self.assertEqual(
            list((repository.parent / "runs").rglob("execution-started.txt")), []
        )

    def test_required_cognition_capability_is_checked_at_prepare_phase(self) -> None:
        root = self._next_root()
        repository = root / "repository"
        _configure_fixture(
            repository, skill_mode="required", project_mode="optional"
        )
        manifest_path = repository / "skills" / "sample" / "manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["capabilities"]["optional"].remove("cognition.execute")
        manifest["capabilities"]["required"].append("cognition.execute")
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        result = AgentRuntime(repository).run(
            task="required cognition capability phase",
            skill_name="sample",
            project_id="test",
            inputs=(),
            run_root=root / "runs",
            capabilities={},
        )
        trace = _read_trace(result)
        self.assertIn("COGNITION_PROVIDER_MISSING", result.validation_errors[0])
        self.assertPhase(trace, "COGNITION_PREPARE", "blocked")
        self.assertNotIn(
            "RUNTIME_CAPABILITY_MISSING", " ".join(result.validation_errors)
        )

    def test_project_may_escalate_optional_cognition_to_required(self) -> None:
        result, trace, _ = run_without_cognition_provider(
            self._next_root(), skill_mode="optional", project_mode="required"
        )
        self.assertIn("COGNITION_PROVIDER_MISSING", result.validation_errors[0])
        self.assertEqual(trace["cognition_policy"]["effective_mode"], "required")

    def test_project_cannot_require_skill_disabled_cognition(self) -> None:
        result, trace, repository = run_without_cognition_provider(
            self._next_root(), skill_mode="disabled", project_mode="required"
        )
        self.assertIn("COGNITION_POLICY_CONFLICT", result.validation_errors[0])
        self.assertEqual(trace["cognition"], [])
        self.assertEqual(
            list((repository.parent / "runs").rglob("execution-started.txt")), []
        )

    def test_disabled_optional_cognition_skips_without_loading_protocols(self) -> None:
        result, trace, _ = run_without_cognition_provider(
            self._next_root(), skill_mode="optional", project_mode="disabled"
        )
        self.assertTrue(result.succeeded, result.to_dict())
        self.assertEqual(trace["cognition_policy"]["effective_mode"], "disabled")
        for record in trace["cognition"]:
            self.assertEqual(record["status"], "skipped")
            self.assertFalse(record["loaded"])
            self.assertEqual(record["reason"], "policy_disabled")

    def test_provider_execution_and_validation_are_separate_trace_facts(self) -> None:
        calls: list[tuple[str, Mapping[str, Any]]] = []

        def provider(
            capability_id: str, payload: Mapping[str, Any]
        ) -> Mapping[str, Any]:
            calls.append((capability_id, payload))
            if payload["phase"] == "prepare":
                return {
                    "outcome": "pass",
                    "proposal": {"criteria": ["bounded", "evidence-backed"]},
                }
            if payload["phase"] == "critique":
                return {"outcome": "pass"}
            return {"outcome": "no_candidate"}

        result, trace, _ = self._run_with_provider(provider)
        self.assertTrue(result.succeeded, result.to_dict())
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(call[0] == "cognition.execute" for call in calls))
        self.assertEqual(
            [call[1]["phase"] for call in calls],
            ["prepare", "critique", "memory_review"],
        )
        self.assertEqual(
            set(calls[0][1]["context"]),
            {"run_id", "project_id", "skill_name", "task", "input_refs"},
        )
        self.assertEqual(
            set(calls[1][1]["context"]),
            {"run_id", "project_id", "skill_name", "artifact_refs"},
        )
        self.assertEqual(
            set(calls[2][1]["context"]),
            {
                "run_id",
                "project_id",
                "skill_name",
                "artifact_refs",
                "validation_completed",
            },
        )
        for phase in (
            "COGNITION_PREPARE",
            "COGNITION_CRITIQUE",
            "MEMORY_REVIEW",
        ):
            record = self.assertPhase(trace, phase, "executed")
            self.assertTrue(record["loaded"])
            self.assertTrue(record["executed"])
            self.assertTrue(record["validated"])
            self.assertFalse(record["changed_run_disposition"])
        self.assertEqual(
            self.assertPhase(trace, "COGNITION_PREPARE", "executed")[
                "proposal_fields"
            ],
            ["criteria"],
        )

    def test_blocked_critique_fails_without_memory_review_or_retry(self) -> None:
        calls: list[str] = []

        def provider(
            capability_id: str, payload: Mapping[str, Any]
        ) -> Mapping[str, Any]:
            calls.append(str(payload["phase"]))
            outcome = "blocked" if payload["phase"] == "critique" else "pass"
            return {"outcome": outcome}

        result, trace, _ = self._run_with_provider(provider)
        self.assertIn("COGNITION_BLOCKED", result.validation_errors[0])
        record = self.assertPhase(trace, "COGNITION_CRITIQUE", "blocked")
        self.assertTrue(record["executed"])
        self.assertTrue(record["validated"])
        self.assertTrue(record["changed_run_disposition"])
        self.assertEqual(calls, ["prepare", "critique"])
        self.assertEqual(
            [item for item in trace["cognition"] if item["phase"] == "MEMORY_REVIEW"],
            [],
        )
        self.assertNotIn("RECOVERY", [item["to"] for item in trace["transitions"]])

    def test_review_required_critique_stops_explicitly(self) -> None:
        def provider(
            capability_id: str, payload: Mapping[str, Any]
        ) -> Mapping[str, Any]:
            if payload["phase"] == "critique":
                return {"outcome": "review_required"}
            return {"outcome": "pass"}

        result, trace, _ = self._run_with_provider(provider)
        self.assertIn("COGNITION_REVIEW_REQUIRED", result.validation_errors[0])
        self.assertPhase(trace, "COGNITION_CRITIQUE", "review_required")
        self.assertEqual(trace["final_state"], "FAILED")

    def test_memory_review_writes_only_run_local_candidate_after_validation(self) -> None:
        observed_validation: list[bool] = []

        def provider(
            capability_id: str, payload: Mapping[str, Any]
        ) -> Mapping[str, Any]:
            if payload["phase"] != "memory_review":
                return {"outcome": "pass"}
            context = payload["context"]
            observed_validation.append(bool(context["validation_completed"]))
            return {
                "outcome": "candidate",
                "memory_candidate": {
                    "schema_version": "1.0",
                    "candidate_id": "candidate-cognition-a",
                    "project_id": context["project_id"],
                    "run_id": context["run_id"],
                    "scope": "project",
                    "target_id": context["project_id"],
                    "proposition": "A generic validated run lesson",
                    "evidence_refs": ["trace/execution_trace.json"],
                    "status": "proposed",
                },
            }

        persistent_before = sorted(
            path.relative_to(REPOSITORY_ROOT).as_posix()
            for path in (REPOSITORY_ROOT / "memory").rglob("*")
        )
        result, trace, _ = self._run_with_provider(provider)
        self.assertTrue(result.succeeded, result.to_dict())
        self.assertEqual(observed_validation, [True])
        record = self.assertPhase(trace, "MEMORY_REVIEW", "executed")
        self.assertEqual(record["provider_outcome"], "candidate")
        self.assertEqual(record["candidate_ref"], "memory/memory_candidate.json")
        candidate_path = result.trace_path.parent.parent / record["candidate_ref"]
        self.assertTrue(candidate_path.is_file())
        self.assertTrue(candidate_path.is_relative_to(result.trace_path.parent.parent))
        self.assertLess(
            [item["to"] for item in trace["transitions"]].index("VALIDATE"),
            [item["to"] for item in trace["transitions"]].index("MEMORY_REVIEW"),
        )
        persistent_after = sorted(
            path.relative_to(REPOSITORY_ROOT).as_posix()
            for path in (REPOSITORY_ROOT / "memory").rglob("*")
        )
        self.assertEqual(persistent_after, persistent_before)

    def test_memory_review_does_not_run_when_validation_fails(self) -> None:
        root = self._next_root()
        repository = root / "repository"
        _configure_fixture(
            repository, skill_mode="optional", project_mode="optional"
        )
        calls: list[str] = []

        def provider(
            capability_id: str, payload: Mapping[str, Any]
        ) -> Mapping[str, Any]:
            calls.append(str(payload["phase"]))
            return {"outcome": "pass"}

        runtime = AgentRuntime(repository)
        runtime.validator.validate_trace = lambda *args, **kwargs: ValidationResult(
            False, ("forced validation failure",)
        )
        result = runtime.run(
            task="validation must precede memory review",
            skill_name="sample",
            project_id="test",
            inputs=(),
            run_root=root / "runs",
            capabilities={"cognition.execute": provider},
        )
        trace = _read_trace(result)
        self.assertIn("TRACE_VALIDATION_FAILED", result.validation_errors[0])
        self.assertEqual(calls, ["prepare", "critique"])
        self.assertEqual(
            [item for item in trace["cognition"] if item["phase"] == "MEMORY_REVIEW"],
            [],
        )

    def test_prepare_cannot_return_contract_or_artifact_mutations(self) -> None:
        def provider(
            capability_id: str, payload: Mapping[str, Any]
        ) -> Mapping[str, Any]:
            return {
                "outcome": "pass",
                "artifacts": {"score": "forbidden"},
            }

        result, trace, repository = self._run_with_provider(provider)
        self.assertIn("COGNITION_RESULT_INVALID", result.validation_errors[0])
        record = self.assertPhase(trace, "COGNITION_PREPARE", "blocked")
        self.assertTrue(record["executed"])
        self.assertFalse(record["validated"])
        self.assertEqual(
            list((repository.parent / "runs").rglob("execution-started.txt")), []
        )

    def test_trace_matches_cognition_aware_execution_schema(self) -> None:
        result, trace, _ = run_without_cognition_provider(self._next_root())
        self.assertTrue(result.succeeded, result.to_dict())
        violations = ContractValidator(REPOSITORY_ROOT).validate(
            trace, REPOSITORY_ROOT / "runtime" / "execution_log.schema.json"
        )
        self.assertEqual(violations, ())

    def test_validator_rejects_false_cognition_execution_proof(self) -> None:
        result, trace, _ = run_without_cognition_provider(self._next_root())
        self.assertTrue(result.succeeded, result.to_dict())
        trace["cognition"][0]["executed"] = True
        checked = ValidatorEngine().validate_trace(
            trace, run_root=result.trace_path.parent.parent
        )
        self.assertFalse(checked.valid)
        self.assertIn("Skipped Cognition record", " ".join(checked.errors))

    def test_validator_rejects_downgraded_cognition_policy(self) -> None:
        result, trace, _ = run_without_cognition_provider(self._next_root())
        self.assertTrue(result.succeeded, result.to_dict())
        trace["cognition_policy"]["skill_mode"] = "required"
        checked = ValidatorEngine().validate_trace(
            trace, run_root=result.trace_path.parent.parent
        )
        self.assertFalse(checked.valid)
        self.assertIn("policy precedence", " ".join(checked.errors))


if __name__ == "__main__":
    unittest.main()
