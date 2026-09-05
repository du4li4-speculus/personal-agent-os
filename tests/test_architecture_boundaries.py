from __future__ import annotations

import ast
import subprocess
import unittest
from pathlib import Path
from typing import Any, Iterable, Mapping

from runtime.contract_validator import ContractValidator
from runtime.entrypoint_loader import EntrypointLoader
from runtime.models import AgentRuntimeError
from runtime.registry_loader import RegistryLoader
from runtime.skill_loader import SkillLoader


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUN_DOCS = {Path("runs/README.md"), Path("runs/.gitignore")}


def _python_files(root: Path) -> tuple[Path, ...]:
    resolved = root if root.is_absolute() else REPOSITORY_ROOT / root
    return tuple(sorted(resolved.rglob("*.py")))


def _matches_prefix(module_name: str, prefixes: Iterable[str]) -> bool:
    return any(
        module_name == prefix
        or module_name.startswith(f"{prefix}.")
        or module_name.startswith(f"{prefix}_")
        or module_name.startswith(f"{prefix}-")
        for prefix in prefixes
    )


def imports_matching(root: Path, prefixes: tuple[str, ...]) -> tuple[str, ...]:
    violations: list[str] = []
    for source_path in _python_files(root):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.as_posix())
        for node in ast.walk(tree):
            modules: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = (node.module,)
            for module_name in modules:
                if _matches_prefix(module_name, prefixes):
                    relative = source_path.relative_to(REPOSITORY_ROOT)
                    violations.append(f"{relative}:{node.lineno}:{module_name}")
    return tuple(sorted(violations))


def source_literals_matching(
    root: Path, forbidden_literals: tuple[str, ...]
) -> tuple[str, ...]:
    violations: list[str] = []
    for source_path in _python_files(root):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.as_posix())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            for forbidden in forbidden_literals:
                if forbidden in node.value:
                    relative = source_path.relative_to(REPOSITORY_ROOT)
                    violations.append(f"{relative}:{node.lineno}:{forbidden}")
    return tuple(sorted(violations))


def tracked_files() -> tuple[Path, ...]:
    completed = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return tuple(
        Path(value.decode("utf-8"))
        for value in completed.stdout.split(b"\0")
        if value
    )


def validate_all_active_skills(repository_root: Path) -> tuple[str, ...]:
    violations: list[str] = []
    registry = RegistryLoader(repository_root)
    skill_loader = SkillLoader(registry)
    entrypoint_loader = EntrypointLoader()
    for name, entry in sorted(registry.load().items()):
        if entry.status != "active":
            continue
        try:
            skill = skill_loader.load(name)
            entrypoint_loader.load(skill)
        except AgentRuntimeError as exc:
            violations.append(f"{name}:{exc.code}:{exc.message}")
    return tuple(violations)


def agent_role_document(**overrides: Any) -> dict[str, Any]:
    document = {
        "schema_version": "1.0",
        "name": "boundary-reviewer",
        "objective": "Audit one accepted architecture boundary",
        "responsibility": "Return evidence-linked boundary violations",
        "inputs": ["repository_state"],
        "outputs": ["boundary_report"],
        "constraints": ["no_domain_knowledge_storage"],
        "evaluation_criteria": ["all_findings_reference_evidence"],
        "why_agent_required": "The audit coordinates multiple bounded checks",
        "why_skill_insufficient": "No single domain Skill owns repository governance",
    }
    document.update(overrides)
    return document


def validate_agent_role(document: Mapping[str, Any]) -> tuple[str, ...]:
    violations = ContractValidator(REPOSITORY_ROOT).validate(
        document, REPOSITORY_ROOT / "contracts" / "agent-role.schema.json"
    )
    return tuple(f"{item.path}:{item.keyword}" for item in violations)


class ArchitectureBoundaryTestCase(unittest.TestCase):
    def test_runtime_does_not_import_domain_skills(self) -> None:
        violations = imports_matching(Path("runtime"), prefixes=("skills", "toefl"))
        self.assertEqual(violations, ())

    def test_no_tracked_run_instance_data_exists(self) -> None:
        tracked = tracked_files()
        forbidden = tuple(
            path
            for path in tracked
            if path.parts and path.parts[0] == "runs" and path not in RUN_DOCS
        )
        self.assertEqual(forbidden, ())

    def test_no_tracked_skill_output_directories_exist(self) -> None:
        tracked = tracked_files()
        forbidden = tuple(
            path
            for path in tracked
            if len(path.parts) >= 3
            and path.parts[0] == "skills"
            and path.parts[2] == "output"
        )
        self.assertEqual(forbidden, ())

    def test_every_active_skill_contract_and_entrypoint_resolves(self) -> None:
        self.assertEqual(validate_all_active_skills(REPOSITORY_ROOT), ())

    def test_development_skill_is_validated_without_execution_authority(self) -> None:
        registry = RegistryLoader(REPOSITORY_ROOT)
        entry = registry.get_registered("toefl-writing-grader")
        skill = SkillLoader(registry).load_registered("toefl-writing-grader")

        self.assertEqual(entry.status, "development")
        self.assertIsNone(skill.contract.entrypoint)
        with self.assertRaises(AgentRuntimeError) as raised:
            registry.get("toefl-writing-grader")
        self.assertEqual(raised.exception.code, "SKILL_NOT_ACTIVE")

    def test_runtime_has_no_persistent_memory_write_target(self) -> None:
        forbidden_literals = ("memory/global", "memory/projects", "memory/skills")
        self.assertEqual(
            source_literals_matching(Path("runtime"), forbidden_literals), ()
        )

    def test_agent_role_contract_rejects_knowledge_container(self) -> None:
        errors = validate_agent_role(
            agent_role_document(
                evaluation_criteria=[],
                why_skill_insufficient="",
            )
        )
        self.assertNotEqual(errors, ())
        self.assertTrue(any("evaluation_criteria" in error for error in errors))
        self.assertTrue(any("why_skill_insufficient" in error for error in errors))

    def test_canonical_architecture_links_current_authorities(self) -> None:
        architecture = (
            REPOSITORY_ROOT / "docs" / "ARCHITECTURE_BOUNDARIES.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Core -> Cognition -> Runtime Control Plane -> Registry -> Skill -> "
            "Project -> Artifacts -> Memory Candidate",
            architecture,
        )
        for reference in (
            "docs/PLAN_STATUS.md",
            "docs/policies/RUNTIME_POLICY.md",
            "docs/policies/MEMORY_POLICY.md",
            "docs/policies/AGENT_ROLE_POLICY.md",
            "docs/policies/PROJECT_BOUNDARY_POLICY.md",
            "docs/TOEFL_SKILL_ACTIVATION_CRITERIA.md",
        ):
            self.assertIn(reference, architecture)

    def test_ci_runs_required_non_production_checks(self) -> None:
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        for trigger_or_permission in (
            "branches: [main]",
            "pull_request:",
            "contents: read",
        ):
            self.assertIn(trigger_or_permission, workflow)
        for command in (
            "python3 -m pip install -r requirements.txt",
            "python3 -m runtime.cli validate-contracts",
            "python3 -m unittest tests.test_architecture_boundaries -v",
            "python3 -m unittest discover -s tests -v",
            "git diff --check",
        ):
            self.assertIn(command, workflow)
        for forbidden in (
            "runtime.cli run",
            "memory/global",
            "memory/projects",
            "memory/skills",
        ):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
