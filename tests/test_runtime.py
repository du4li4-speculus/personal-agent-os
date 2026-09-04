from __future__ import annotations

import json
import os
import shutil
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
SAMPLE_SKILL = "sample"
SAMPLE_OUTPUTS = ("result.txt",)


def write_active_sample_repository(
    root: Path, *, registry_version: str = "1.0.0", manifest_version: str = "1.0.0"
) -> None:
    shutil.copytree(REPOSITORY_ROOT / "contracts", root / "contracts")
    registry_dir = root / "registry"
    runtime_dir = root / "runtime"
    skill_dir = root / "skills" / SAMPLE_SKILL
    schema_dir = skill_dir / "schemas"
    source_dir = skill_dir / "src"
    registry_dir.mkdir(parents=True)
    runtime_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    shutil.copy2(
        REPOSITORY_ROOT / "runtime" / "state_machine.yaml",
        runtime_dir / "state_machine.yaml",
    )
    (registry_dir / "skill_registry.yaml").write_text(
        "schema_version: \"1.0\"\n"
        "skills:\n"
        "  sample:\n"
        f"    version: \"{registry_version}\"\n"
        "    status: active\n"
        "    path: skills/sample\n"
        "    manifest: manifest.yaml\n",
        encoding="utf-8",
    )
    (skill_dir / "manifest.yaml").write_text(
        "schema_version: \"1.0\"\n"
        "name: sample\n"
        f"version: \"{manifest_version}\"\n"
        "kind: workflow\n"
        "entrypoint:\n"
        "  python_path: src\n"
        "  module: sample_entry\n"
        "  callable: execute\n"
        "inputs:\n"
        "  contract: schemas/input.schema.json\n"
        "  accepted_formats: [text]\n"
        "intermediate_outputs: []\n"
        "outputs:\n"
        "  - name: result\n"
        "    path: result.txt\n"
        "capabilities:\n"
        "  required: [runtime.execution_proof, runtime.validation]\n"
        "  optional: []\n"
        "cognition:\n"
        "  mode: optional\n"
        "  prepare: [decision]\n"
        "  critique: [critique]\n"
        "  memory_review: memory\n",
        encoding="utf-8",
    )
    (skill_dir / "SKILL.md").write_text(
        "# Sample runtime test Skill\n", encoding="utf-8"
    )
    (schema_dir / "input.schema.json").write_text(
        '{"$schema": "https://json-schema.org/draft/2020-12/schema"}\n',
        encoding="utf-8",
    )
    (source_dir / "sample_entry.py").write_text(
        "def execute(context):\n    return {}\n", encoding="utf-8"
    )


class RuntimeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repository_root = Path(self.temp_dir.name) / "repository"
        write_active_sample_repository(self.repository_root)
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.runtime = AgentRuntime(self.repository_root)

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
        self.assertIn("Sample runtime test Skill", skill.definition)

    def test_skill_loader_rejects_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
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
            skill_name=SAMPLE_SKILL,
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
            skill_name=SAMPLE_SKILL,
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
            skill_name=SAMPLE_SKILL,
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
            skill_name=SAMPLE_SKILL,
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
            skill_name=SAMPLE_SKILL,
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
                SAMPLE_SKILL,
                "--output-dir",
                str(self.output_dir),
                "--repository-root",
                str(self.repository_root),
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
