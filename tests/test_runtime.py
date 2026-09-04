from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

from runtime.artifact_manager import ArtifactManager
from runtime.capabilities import CapabilitySet
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
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "active-skill-repository"
SAMPLE_SKILL = "sample"
SAMPLE_OUTPUTS = ("result.txt",)


def write_active_sample_repository(
    root: Path, *, registry_version: str = "1.0.0", manifest_version: str = "1.0.0"
) -> None:
    shutil.copytree(FIXTURE_ROOT, root)
    shutil.copytree(REPOSITORY_ROOT / "contracts", root / "contracts")
    shutil.copytree(REPOSITORY_ROOT / "cognition", root / "cognition")
    runtime_dir = root / "runtime"
    runtime_dir.mkdir(parents=True)
    shutil.copy2(
        REPOSITORY_ROOT / "runtime" / "state_machine.yaml",
        runtime_dir / "state_machine.yaml",
    )
    project_dir = root / "projects" / "test"
    project_dir.mkdir(parents=True)
    (project_dir / "project.yaml").write_text(
        'schema_version: "1.0"\n'
        "project_id: test\n"
        "allowed_skills: [sample]\n"
        "cognition_mode: optional\n"
        "memory_policy: candidate_only\n",
        encoding="utf-8",
    )
    registry_path = root / "registry" / "skill_registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registry["skills"][SAMPLE_SKILL]["version"] = registry_version
    registry_path.write_text(
        yaml.safe_dump(registry, sort_keys=False), encoding="utf-8"
    )
    manifest_path = root / "skills" / SAMPLE_SKILL / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = manifest_version
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )


class RuntimeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repository_root = Path(self.temp_dir.name) / "repository"
        write_active_sample_repository(self.repository_root)
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.runtime = AgentRuntime(self.repository_root)

    def _run(self, *, task: str = "Run the registered fixture") -> RunResult:
        return self.runtime.run(
            task=task,
            skill_name=SAMPLE_SKILL,
            project_id="test",
            inputs=(),
            run_root=self.output_dir,
            capabilities={},
        )

    def test_registry_discovers_active_skill(self) -> None:
        entry = RegistryLoader(self.repository_root).get(SAMPLE_SKILL)
        self.assertEqual(entry.version, "1.0.0")
        self.assertTrue(entry.resolved_path.is_dir())

    def test_registry_rejects_unknown_skill(self) -> None:
        with self.assertRaisesRegex(Exception, "not registered"):
            RegistryLoader(REPOSITORY_ROOT).get("missing-skill")

    def test_registry_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(REPOSITORY_ROOT / "contracts", root / "contracts")
            (root / "registry").mkdir()
            (root / "skills").mkdir()
            (root / "outside").mkdir()
            (root / "skills" / "escaped").symlink_to(
                root / "outside", target_is_directory=True
            )
            (root / "registry" / "skill_registry.yaml").write_text(
                "schema_version: \"1.0\"\n"
                "skills:\n"
                "  escaped:\n"
                "    version: \"1.0.0\"\n"
                "    status: active\n"
                "    path: skills/escaped\n"
                "    manifest: manifest.yaml\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(Exception, "escapes"):
                RegistryLoader(root).load()

    def test_skill_loader_reads_contract(self) -> None:
        skill = SkillLoader(RegistryLoader(self.repository_root)).load(SAMPLE_SKILL)
        self.assertEqual(skill.version, "1.0.0")
        self.assertEqual(skill.outputs, SAMPLE_OUTPUTS)
        self.assertIn("Sample fixture Skill", skill.definition)

    def test_skill_loader_rejects_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            write_active_sample_repository(
                root, registry_version="1.0.0", manifest_version="2.0.0"
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
            "COGNITION_PREPARE",
            "EXECUTE",
            "ARTIFACT",
            "COGNITION_CRITIQUE",
            "VALIDATE",
            "MEMORY_REVIEW",
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
        result = self._run()
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
                "COGNITION_PREPARE",
                "EXECUTE",
                "ARTIFACT",
                "COGNITION_CRITIQUE",
                "VALIDATE",
                "MEMORY_REVIEW",
                "DELIVER",
            ],
        )
        self.assertTrue(all(trace["proof"].values()))
        self.assertTrue(ValidatorEngine().validate_trace_file(result.trace_path).valid)

    def test_missing_artifact_fails_closed_with_trace(self) -> None:
        entrypoint_path = (
            self.repository_root
            / "skills"
            / SAMPLE_SKILL
            / "src"
            / "sample_skill"
            / "entrypoint.py"
        )
        entrypoint_path.write_text(
            "from runtime.models import SkillExecutionResult\n"
            "def execute(context, skill, capabilities):\n"
            "    return SkillExecutionResult({}, {})\n",
            encoding="utf-8",
        )
        result = self._run(task="Missing artifact test")
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.final_state, "FAILED")
        self.assertIsNotNone(result.trace_path)
        trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "FAILED")
        self.assertEqual(trace["errors"][-1]["code"], "ARTIFACT_MISSING")

    def test_entrypoint_exception_fails_closed(self) -> None:
        entrypoint_path = (
            self.repository_root
            / "skills"
            / SAMPLE_SKILL
            / "src"
            / "sample_skill"
            / "entrypoint.py"
        )
        entrypoint_path.write_text(
            "def execute(context, skill, capabilities):\n"
            "    raise ValueError('fixture entrypoint broke')\n",
            encoding="utf-8",
        )
        result = self._run(task="Entrypoint failure test")
        self.assertEqual(result.final_state, "FAILED")
        self.assertTrue(any("EXECUTION_FAILED" in error for error in result.validation_errors))

    def test_runtime_readiness_retries_once(self) -> None:
        original_check = self.runtime._runtime_check
        calls = {"count": 0}

        def flaky_check(
            context: Any, skill: LoadedSkill, capabilities: CapabilitySet
        ) -> None:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeReadinessError("temporary readiness issue")
            original_check(context, skill, capabilities)

        self.runtime._runtime_check = flaky_check  # type: ignore[method-assign]

        result = self._run(task="Recovery test")
        self.assertTrue(result.succeeded, result.to_dict())
        self.assertEqual(calls["count"], 2)
        trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
        self.assertIn("RECOVERY", [item["to"] for item in trace["transitions"]])

    def test_validator_rejects_incomplete_proof(self) -> None:
        result = self._run(task="Proof validation test")
        trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
        trace["proof"]["execution_traced"] = False
        run_instance = result.trace_path.parent.parent
        validation = ValidatorEngine().validate_trace(
            trace, run_root=run_instance
        )
        self.assertFalse(validation.valid)
        self.assertIn("execution_traced", " ".join(validation.errors))

    def test_cli_trace_validation(self) -> None:
        result = self._run(task="CLI trace validation test")
        self.assertTrue(result.succeeded, result.to_dict())
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(REPOSITORY_ROOT)
        validate = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli",
                "validate-trace",
                "--trace",
                str(result.trace_path),
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

        trace = json.loads(result.trace_path.read_text())
        trace["status"] = "FAILED"
        corrupted = result.trace_path.parent / "corrupted-trace.json"
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
