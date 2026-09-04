from __future__ import annotations

import inspect
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

import yaml

from runtime.models import CapabilityProvider, RunResult
from runtime.runner import AgentRuntime


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "active-skill-repository"


class EntrypointLoaderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self._fixture_counter = 0
        self.last_repository_root: Path | None = None

    def _copy_fixture_repository(self) -> Path:
        self._fixture_counter += 1
        root = Path(self.temp_dir.name) / f"repository-{self._fixture_counter}"
        shutil.copytree(FIXTURE_ROOT, root)
        shutil.copytree(REPOSITORY_ROOT / "contracts", root / "contracts")
        (root / "runtime").mkdir()
        shutil.copy2(
            REPOSITORY_ROOT / "runtime" / "state_machine.yaml",
            root / "runtime" / "state_machine.yaml",
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
        self.last_repository_root = root
        return root

    def _execute(
        self,
        root: Path,
        *,
        capabilities: Mapping[str, CapabilityProvider] | None = None,
    ) -> RunResult:
        return AgentRuntime(root).run(
            task="fixture",
            skill_name="sample",
            project_id="test",
            inputs=(),
            run_root=root / "run",
            capabilities=capabilities or {},
        )

    def run_fixture(
        self,
        *,
        entrypoint_python_path: str | None = None,
        entrypoint_module: str | None = None,
        entrypoint_callable: str | None = None,
        required_capabilities: tuple[str, ...] | None = None,
        optional_capabilities: tuple[str, ...] | None = None,
        capabilities: Mapping[str, CapabilityProvider] | None = None,
    ) -> RunResult:
        root = self._copy_fixture_repository()
        manifest_path = root / "skills" / "sample" / "manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if entrypoint_python_path is not None:
            manifest["entrypoint"]["python_path"] = entrypoint_python_path
        if entrypoint_module is not None:
            manifest["entrypoint"]["module"] = entrypoint_module
        if entrypoint_callable is not None:
            manifest["entrypoint"]["callable"] = entrypoint_callable
        if required_capabilities is not None:
            manifest["capabilities"]["required"] = list(required_capabilities)
        if optional_capabilities is not None:
            manifest["capabilities"]["optional"] = list(optional_capabilities)
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        return self._execute(root, capabilities=capabilities)

    def test_active_fixture_executes_without_caller_executor(self) -> None:
        self.assertNotIn("executor", inspect.signature(AgentRuntime.run).parameters)
        result = self.run_fixture()
        self.assertTrue(result.succeeded, result.to_dict())

    def test_entrypoint_path_escape_is_rejected(self) -> None:
        result = self.run_fixture(entrypoint_python_path="../outside")
        self.assertIn("ENTRYPOINT_PATH_ESCAPE", result.validation_errors[0])

    def test_absolute_entrypoint_path_is_rejected(self) -> None:
        result = self.run_fixture(entrypoint_python_path="/tmp/outside")
        self.assertIn("ENTRYPOINT_PATH_ESCAPE", result.validation_errors[0])

    def test_imported_module_file_must_remain_inside_skill_root(self) -> None:
        root = self._copy_fixture_repository()
        outside = root.parent / "outside-entrypoint.py"
        side_effect = root.parent / "outside-module-executed.txt"
        outside.write_text(
            "from pathlib import Path\n"
            f"Path({str(side_effect)!r}).write_text('executed', encoding='utf-8')\n"
            "def execute(context, skill, capabilities):\n    raise AssertionError\n",
            encoding="utf-8",
        )
        entrypoint = (
            root
            / "skills"
            / "sample"
            / "src"
            / "sample_skill"
            / "entrypoint.py"
        )
        entrypoint.unlink()
        entrypoint.symlink_to(outside)
        result = self._execute(root)
        self.assertIn("ENTRYPOINT_MODULE_ESCAPE", result.validation_errors[0])
        self.assertFalse(side_effect.exists())

    def test_missing_entrypoint_callable_is_rejected(self) -> None:
        result = self.run_fixture(entrypoint_callable="missing")
        self.assertIn("ENTRYPOINT_CALLABLE_INVALID", result.validation_errors[0])

    def test_dynamic_loading_does_not_mutate_sys_path(self) -> None:
        before = list(sys.path)
        result = self.run_fixture()
        self.assertTrue(result.succeeded, result.to_dict())
        self.assertEqual(sys.path, before)

    def test_missing_required_capability_fails_before_execute(self) -> None:
        result = self.run_fixture(required_capabilities=("missing.capability",))
        self.assertIn("RUNTIME_CAPABILITY_MISSING", result.validation_errors[0])
        markers = list(
            (self.last_repository_root / "run").rglob("execution-started.txt")
        )
        self.assertEqual(markers, [])

    def test_optional_capability_remains_optional(self) -> None:
        result = self.run_fixture(optional_capabilities=("missing.optional",))
        self.assertTrue(result.succeeded, result.to_dict())

    def test_registered_capability_provider_is_available_to_skill(self) -> None:
        calls: list[tuple[str, Mapping[str, Any]]] = []

        def echo_provider(
            capability_id: str, payload: Mapping[str, Any]
        ) -> Mapping[str, Any]:
            calls.append((capability_id, payload))
            return {"echo": payload["value"]}

        result = self.run_fixture(
            required_capabilities=("fixture.echo",),
            optional_capabilities=(),
            capabilities={"fixture.echo": echo_provider},
        )
        self.assertTrue(result.succeeded, result.to_dict())
        self.assertEqual(calls, [("fixture.echo", {"value": "registered-entrypoint"})])


if __name__ == "__main__":
    unittest.main()
