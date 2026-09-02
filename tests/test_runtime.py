from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from runtime.artifact_manager import ArtifactManager
from runtime.models import (
    ArtifactValidationError,
    LoadedSkill,
    RunResult,
    RuntimeReadinessError,
)
from runtime.registry_loader import RegistryLoader
from runtime.runner import AgentRuntime
from runtime.skill_loader import SkillLoader
from runtime.state_manager import StateManager
from runtime.validator_engine import ValidatorEngine


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOEFL_OUTPUTS = (
    "assessment.json",
    "diagnosis.json",
    "learning_loop.json",
    "student_report.pdf",
    "parent_report.pdf",
    "teacher_dashboard.json",
)


class RuntimeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.runtime = AgentRuntime(REPOSITORY_ROOT)

    def _write_artifacts(
        self, context: Any, skill: LoadedSkill, *, missing: str | None = None
    ) -> Mapping[str, Path]:
        returned: dict[str, Path] = {}
        for name in skill.outputs:
            if name == missing:
                continue
            path = context.output_dir / name
            path.write_text(f"fixture: {name}\n", encoding="utf-8")
            returned[name] = Path(name)
        return returned

    def test_registry_discovers_active_skill(self) -> None:
        entry = RegistryLoader(REPOSITORY_ROOT).get("toefl-writing-grader")
        self.assertEqual(entry.version, "2.0.0")
        self.assertTrue(entry.resolved_path.is_dir())

    def test_registry_rejects_unknown_skill(self) -> None:
        with self.assertRaisesRegex(Exception, "not registered"):
            RegistryLoader(REPOSITORY_ROOT).get("missing-skill")

    def test_registry_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "registry").mkdir()
            (root / "skills").mkdir()
            (root / "outside").mkdir()
            (root / "registry" / "skill_registry.yaml").write_text(
                "skills:\n"
                "  escaped:\n"
                "    version: 1.0.0\n"
                "    type: test\n"
                "    status: active\n"
                "    path: skills/../outside\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(Exception, "escapes"):
                RegistryLoader(root).load()

    def test_skill_loader_reads_contract(self) -> None:
        skill = SkillLoader(RegistryLoader(REPOSITORY_ROOT)).load(
            "toefl-writing-grader"
        )
        self.assertEqual(skill.version, "2.0.0")
        self.assertEqual(skill.outputs, TOEFL_OUTPUTS)
        self.assertIn("Never assess without source evidence", skill.definition)

    def test_skill_loader_rejects_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_dir = root / "skills" / "sample"
            skill_dir.mkdir(parents=True)
            (root / "registry").mkdir()
            (skill_dir / "SKILL.md").write_text("# Sample\n", encoding="utf-8")
            (skill_dir / "manifest.yaml").write_text(
                "name: sample\n"
                "version: 2.0.0\n"
                "type: assessment\n"
                "outputs: [result.json]\n"
                "requires: []\n",
                encoding="utf-8",
            )
            (root / "registry" / "skill_registry.yaml").write_text(
                "skills:\n"
                "  sample:\n"
                "    version: 1.0.0\n"
                "    type: assessment\n"
                "    status: active\n"
                "    path: skills/sample\n",
                encoding="utf-8",
            )
            loader = SkillLoader(RegistryLoader(root))
            with self.assertRaisesRegex(Exception, "version"):
                loader.load("sample")

    def test_state_manager_walks_happy_path(self) -> None:
        manager = StateManager.from_file(REPOSITORY_ROOT / "runtime" / "state_machine.yaml")
        path = [
            "IDENTIFY_TASK",
            "FIND_SKILL",
            "LOAD_SKILL",
            "RUNTIME_CHECK",
            "EXECUTE",
            "ARTIFACT",
            "VALIDATE",
            "DELIVER",
        ]
        for state in path:
            manager.transition(state)
        self.assertTrue(manager.is_terminal())

    def test_state_manager_rejects_illegal_transition(self) -> None:
        manager = StateManager.from_file(REPOSITORY_ROOT / "runtime" / "state_machine.yaml")
        with self.assertRaisesRegex(Exception, "Illegal transition"):
            manager.transition("EXECUTE")

    def test_state_manager_allows_one_recovery_retry(self) -> None:
        manager = StateManager.from_file(REPOSITORY_ROOT / "runtime" / "state_machine.yaml")
        manager.transition("IDENTIFY_TASK")
        manager.transition("FIND_SKILL")
        manager.transition("LOAD_SKILL")
        manager.transition("RUNTIME_CHECK")
        self.assertTrue(manager.can_recover())
        manager.transition("RECOVERY")
        self.assertFalse(manager.can_recover())
        manager.transition("RUNTIME_CHECK")
        with self.assertRaisesRegex(Exception, "exhausted"):
            manager.transition("RECOVERY")
        manager.transition("FAILED")
        self.assertTrue(manager.is_terminal())

    def test_artifact_manager_rejects_missing_and_escape(self) -> None:
        self.output_dir.mkdir()
        manager = ArtifactManager(self.output_dir)
        with self.assertRaisesRegex(ArtifactValidationError, "Missing"):
            manager.validate(("result.json",), {})
        outside = Path(self.temp_dir.name) / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        with self.assertRaisesRegex(ArtifactValidationError, "escapes"):
            manager.validate(("result.json",), {"result.json": Path("../outside.txt")})

    def test_successful_end_to_end_run_produces_delivery_proof(self) -> None:
        def executor(context: Any, skill: LoadedSkill) -> Mapping[str, Path]:
            return self._write_artifacts(context, skill)

        result = self.runtime.run(
            task="Run the test adapter",
            skill_name="toefl-writing-grader",
            executor=executor,
            output_dir=self.output_dir,
        )
        self.assertTrue(result.succeeded, result.to_dict())
        self.assertIsNotNone(result.trace_path)
        trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["final_state"], "DELIVER")
        self.assertEqual(
            [item["to"] for item in trace["transitions"]],
            [
                "CREATED",
                "IDENTIFY_TASK",
                "FIND_SKILL",
                "LOAD_SKILL",
                "RUNTIME_CHECK",
                "EXECUTE",
                "ARTIFACT",
                "VALIDATE",
                "DELIVER",
            ],
        )
        self.assertTrue(all(trace["proof"].values()))
        self.assertTrue(ValidatorEngine().validate_trace_file(result.trace_path).valid)

    def test_missing_artifact_fails_closed_with_trace(self) -> None:
        def executor(context: Any, skill: LoadedSkill) -> Mapping[str, Path]:
            return self._write_artifacts(context, skill, missing=skill.outputs[0])

        result = self.runtime.run(
            task="Missing artifact test",
            skill_name="toefl-writing-grader",
            executor=executor,
            output_dir=self.output_dir,
        )
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.final_state, "FAILED")
        self.assertIsNotNone(result.trace_path)
        trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "FAILED")
        self.assertEqual(trace["errors"][-1]["code"], "ARTIFACT_MISSING")

    def test_executor_exception_fails_closed(self) -> None:
        def executor(context: Any, skill: LoadedSkill) -> Mapping[str, Path]:
            raise ValueError("adapter broke")

        result = self.runtime.run(
            task="Executor failure test",
            skill_name="toefl-writing-grader",
            executor=executor,
            output_dir=self.output_dir,
        )
        self.assertEqual(result.final_state, "FAILED")
        self.assertTrue(any("EXECUTION_FAILED" in error for error in result.validation_errors))

    def test_runtime_readiness_retries_once(self) -> None:
        original_check = self.runtime._runtime_check
        calls = {"count": 0}

        def flaky_check(context: Any, skill: LoadedSkill) -> None:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeReadinessError("temporary readiness issue")
            original_check(context, skill)

        self.runtime._runtime_check = flaky_check  # type: ignore[method-assign]

        result = self.runtime.run(
            task="Recovery test",
            skill_name="toefl-writing-grader",
            executor=lambda context, skill: self._write_artifacts(context, skill),
            output_dir=self.output_dir,
        )
        self.assertTrue(result.succeeded, result.to_dict())
        self.assertEqual(calls["count"], 2)
        trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
        self.assertIn("RECOVERY", [item["to"] for item in trace["transitions"]])

    def test_validator_rejects_incomplete_proof(self) -> None:
        def executor(context: Any, skill: LoadedSkill) -> Mapping[str, Path]:
            return self._write_artifacts(context, skill)

        result = self.runtime.run(
            task="Proof validation test",
            skill_name="toefl-writing-grader",
            executor=executor,
            output_dir=self.output_dir,
        )
        trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
        trace["proof"]["execution_traced"] = False
        validation = ValidatorEngine().validate_trace(
            trace, output_dir=self.output_dir
        )
        self.assertFalse(validation.valid)
        self.assertIn("execution_traced", " ".join(validation.errors))

    def test_cli_demo_and_validation(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(REPOSITORY_ROOT)
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli",
                "run-demo",
                "--skill",
                "toefl-writing-grader",
                "--output-dir",
                str(self.output_dir),
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        validate = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli",
                "validate-trace",
                "--trace",
                str(self.output_dir / "execution_trace.json"),
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

        trace = json.loads((self.output_dir / "execution_trace.json").read_text())
        trace["status"] = "FAILED"
        corrupted = self.output_dir / "corrupted-trace.json"
        corrupted.write_text(json.dumps(trace), encoding="utf-8")
        invalid = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli",
                "validate-trace",
                "--trace",
                str(corrupted),
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(invalid.returncode, 0)


if __name__ == "__main__":
    unittest.main()
