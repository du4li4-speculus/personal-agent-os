from __future__ import annotations

import hashlib
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
from runtime.contract_validator import ContractValidator
from runtime.memory_manager import MemoryManager
from runtime.models import AgentRuntimeError, ArtifactValidationError, InputRef
from runtime.project_loader import ProjectLoader
from runtime.run_store import RunStore
from runtime.runner import AgentRuntime


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "active-skill-repository"


class DataBoundaryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_root = Path(self.temp_dir.name)
        self.run_root = self.temp_root / "runs"

    def _fixture_repository(self) -> Path:
        root = self.temp_root / "repository"
        shutil.copytree(FIXTURE_ROOT, root)
        shutil.copytree(REPOSITORY_ROOT / "contracts", root / "contracts")
        shutil.copytree(REPOSITORY_ROOT / "cognition", root / "cognition")
        (root / "runtime").mkdir()
        shutil.copy2(
            REPOSITORY_ROOT / "runtime" / "state_machine.yaml",
            root / "runtime" / "state_machine.yaml",
        )
        project_dir = root / "projects" / "test"
        project_dir.mkdir(parents=True)
        (project_dir / "project.yaml").write_text(
            "schema_version: \"1.0\"\n"
            "project_id: test\n"
            "allowed_skills: [sample]\n"
            "cognition_mode: optional\n"
            "memory_policy: candidate_only\n",
            encoding="utf-8",
        )
        return root

    @staticmethod
    def _candidate_payload(paths: Any) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "candidate_id": "candidate-a",
            "project_id": paths.root.parent.name,
            "run_id": paths.root.name,
            "scope": "project",
            "target_id": paths.root.parent.name,
            "proposition": "Evidence-backed reusable lesson",
            "evidence_refs": ["trace/execution_trace.json"],
            "status": "proposed",
        }

    def test_run_store_keeps_all_paths_under_run_root(self) -> None:
        paths = RunStore(self.run_root).create("project-a", "run-a")
        self.assertEqual(
            paths.root, (self.run_root / "project-a" / "run-a").resolve()
        )
        for path in (
            paths.input_dir,
            paths.work_dir,
            paths.artifact_dir,
            paths.trace_dir,
            paths.memory_dir,
        ):
            self.assertTrue(path.is_dir())
            self.assertTrue(path.is_relative_to(paths.root))

    def test_run_store_rejects_project_and_run_path_escape(self) -> None:
        store = RunStore(self.run_root)
        for project_id, run_id, code in (
            ("../outside", "run-a", "PROJECT_ID_INVALID"),
            ("project-a", "../outside", "RUN_ID_INVALID"),
        ):
            with self.subTest(project_id=project_id, run_id=run_id):
                with self.assertRaises(AgentRuntimeError) as raised:
                    store.create(project_id, run_id)
                self.assertEqual(raised.exception.code, code)

    def test_run_store_rejects_symlink_escape(self) -> None:
        self.run_root.mkdir()
        outside = self.temp_root / "outside"
        outside.mkdir()
        (self.run_root / "project-a").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(AgentRuntimeError) as raised:
            RunStore(self.run_root).create("project-a", "run-a")
        self.assertEqual(raised.exception.code, "RUN_PATH_ESCAPE")

    def test_inputs_are_copied_and_hashed_without_original_path(self) -> None:
        source = self.temp_root / "student-name-source.txt"
        source.write_text("private fixture input\n", encoding="utf-8")
        paths = RunStore(self.run_root).create("project-a", "run-a")
        staged = RunStore(self.run_root).stage_inputs(
            paths, (InputRef(source, "response", "text/plain"),)
        )
        self.assertEqual(len(staged), 1)
        self.assertTrue(staged[0].path.is_relative_to(paths.input_dir))
        self.assertNotEqual(staged[0].path, source)
        self.assertEqual(staged[0].path.read_bytes(), source.read_bytes())

        manifest_text = (paths.input_dir / "manifest.json").read_text(encoding="utf-8")
        manifest = json.loads(manifest_text)
        self.assertNotIn(str(source), manifest_text)
        self.assertNotIn(source.name, manifest_text)
        self.assertEqual(
            manifest["inputs"][0]["sha256"],
            hashlib.sha256(source.read_bytes()).hexdigest(),
        )

    def test_project_loader_accepts_only_declarative_registered_selection(self) -> None:
        project = ProjectLoader(REPOSITORY_ROOT).load("toefl-writing")
        self.assertEqual(project.project_id, "toefl-writing")
        self.assertEqual(project.allowed_skills, ("toefl-writing-grader",))
        self.assertEqual(project.memory_policy, "candidate_only")

        project_file = REPOSITORY_ROOT / "projects" / "toefl-writing" / "project.yaml"
        document = yaml.safe_load(project_file.read_text(encoding="utf-8"))
        self.assertEqual(
            set(document),
            {
                "schema_version",
                "project_id",
                "allowed_skills",
                "cognition_mode",
                "memory_policy",
            },
        )

    def test_memory_review_writes_candidate_only_inside_run(self) -> None:
        paths = RunStore(self.run_root).create("project-a", "run-a")
        trace = paths.trace_dir / "execution_trace.json"
        trace.write_text("{}\n", encoding="utf-8")
        manager = MemoryManager(REPOSITORY_ROOT)
        candidate = manager.write_candidate(paths, self._candidate_payload(paths))
        self.assertEqual(candidate, paths.memory_dir / "memory_candidate.json")
        self.assertTrue(candidate.is_relative_to(paths.memory_dir))
        self.assertEqual(json.loads(candidate.read_text())["status"], "proposed")

    def test_memory_candidate_rejects_scope_escape_and_promotion(self) -> None:
        paths = RunStore(self.run_root).create("project-a", "run-a")
        trace = paths.trace_dir / "execution_trace.json"
        trace.write_text("{}\n", encoding="utf-8")
        manager = MemoryManager(REPOSITORY_ROOT)
        promoted = self._candidate_payload(paths)
        promoted["status"] = "promoted"
        with self.assertRaises(AgentRuntimeError) as raised:
            manager.write_candidate(paths, promoted)
        self.assertEqual(raised.exception.code, "MEMORY_CANDIDATE_SCHEMA_INVALID")

        paths.memory_dir.rmdir()
        outside = self.temp_root / "outside-memory"
        outside.mkdir()
        paths.memory_dir.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(AgentRuntimeError) as raised:
            manager.write_candidate(paths, self._candidate_payload(paths))
        self.assertEqual(raised.exception.code, "MEMORY_CANDIDATE_PATH_ESCAPE")

    def test_runtime_exposes_no_persistent_memory_writer(self) -> None:
        self.assertFalse(hasattr(MemoryManager, "promote"))
        self.assertFalse(hasattr(MemoryManager, "write_persistent"))

    def test_runtime_stages_inputs_and_contains_outputs_and_trace(self) -> None:
        repository = self._fixture_repository()
        source = self.temp_root / "external-input.txt"
        source.write_text("fixture source\n", encoding="utf-8")
        result = AgentRuntime(repository).run(
            task="boundary integration",
            skill_name="sample",
            project_id="test",
            inputs=(InputRef(source, "source", "text/plain"),),
            run_root=self.run_root,
            capabilities={},
        )
        self.assertTrue(result.succeeded, result.to_dict())
        run_instance = result.trace_path.parent.parent
        self.assertEqual(run_instance.parent.parent, self.run_root.resolve())
        self.assertEqual(result.trace_path.parent.name, "trace")
        self.assertTrue((run_instance / "input" / "manifest.json").is_file())
        self.assertTrue(all(path.startswith("artifacts/") for path in result.artifacts.values()))
        for path in run_instance.rglob("*"):
            self.assertTrue(path.resolve().is_relative_to(run_instance.resolve()))

        trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
        violations = ContractValidator(REPOSITORY_ROOT).validate(
            trace, REPOSITORY_ROOT / "runtime" / "execution_log.schema.json"
        )
        self.assertEqual(violations, ())
        run_record_violations = ContractValidator(REPOSITORY_ROOT).validate(
            trace["run_record"],
            REPOSITORY_ROOT / "contracts" / "run-record.schema.json",
        )
        self.assertEqual(run_record_violations, ())
        self.assertNotIn(str(source), json.dumps(trace))
        self.assertTrue(all(ref.startswith("input/") for ref in trace["input_refs"]))
        self.assertFalse((run_instance / "memory" / "memory_candidate.json").exists())

    def test_artifact_manager_rejects_paths_outside_owned_directory(self) -> None:
        paths = RunStore(self.run_root).create("project-a", "run-a")
        outside = self.temp_root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        with self.assertRaises(ArtifactValidationError) as raised:
            ArtifactManager(paths.work_dir, run_root=paths.root).validate(
                ("work.txt",), {"work.txt": outside}
            )
        self.assertEqual(raised.exception.code, "ARTIFACT_PATH_ABSOLUTE")

    def test_cli_uses_managed_project_and_run_boundaries(self) -> None:
        repository = self._fixture_repository()
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(REPOSITORY_ROOT)
        common = {
            "cwd": REPOSITORY_ROOT,
            "env": environment,
            "capture_output": True,
            "text": True,
        }
        listed = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli",
                "list-skills",
                "--repository-root",
                str(repository),
            ],
            **common,
        )
        self.assertEqual(listed.returncode, 0, listed.stdout + listed.stderr)
        validated = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli",
                "validate-contracts",
                "--repository-root",
                str(repository),
            ],
            **common,
        )
        self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
        executed = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli",
                "run",
                "--repository-root",
                str(repository),
                "--project",
                "test",
                "--skill",
                "sample",
                "--run-root",
                str(self.run_root),
            ],
            **common,
        )
        self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
        payload = json.loads(executed.stdout)
        self.assertTrue(
            Path(payload["trace_path"]).resolve().is_relative_to(self.run_root.resolve())
        )


if __name__ == "__main__":
    unittest.main()
