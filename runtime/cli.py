"""Command-line entry points for managed Agent OS execution and validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .models import AgentRuntimeError, InputRef
from .project_loader import ProjectLoader
from .registry_loader import RegistryLoader
from .runner import AgentRuntime
from .skill_loader import SkillLoader
from .validator_engine import ValidatorEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal Agent OS runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_skills = subparsers.add_parser(
        "list-skills", help="list Registry-owned Skill identities and statuses"
    )
    list_skills.add_argument("--repository-root", type=Path, default=Path.cwd())

    validate_contracts = subparsers.add_parser(
        "validate-contracts", help="validate Registry, Skill, and Project contracts"
    )
    validate_contracts.add_argument(
        "--repository-root", type=Path, default=Path.cwd()
    )

    run = subparsers.add_parser(
        "run", help="execute a Project-authorized registered Skill in a new run"
    )
    run.add_argument("--repository-root", type=Path, default=Path.cwd())
    run.add_argument("--project", required=True)
    run.add_argument("--skill", required=True)
    run.add_argument("--input", action="append", default=[], metavar="ROLE=PATH")
    run.add_argument("--run-root", type=Path)

    validate_trace = subparsers.add_parser(
        "validate-trace", help="validate a persisted successful execution trace"
    )
    validate_trace.add_argument("--trace", type=Path, required=True)
    return parser


def _parse_inputs(values: Sequence[str]) -> tuple[InputRef, ...]:
    parsed: list[InputRef] = []
    for value in values:
        if "=" not in value:
            raise AgentRuntimeError(
                f"Input must use ROLE=PATH syntax: {value!r}",
                code="CLI_INPUT_INVALID",
            )
        role, raw_path = value.split("=", 1)
        if not role.strip() or not raw_path.strip():
            raise AgentRuntimeError(
                f"Input must use non-empty ROLE=PATH values: {value!r}",
                code="CLI_INPUT_INVALID",
            )
        parsed.append(InputRef(path=Path(raw_path), role=role.strip()))
    return tuple(parsed)


def _list_skills(repository_root: Path) -> dict[str, object]:
    entries = RegistryLoader(repository_root).load()
    return {
        "skills": [
            {
                "name": entry.name,
                "version": entry.version,
                "status": entry.status,
            }
            for entry in entries.values()
        ]
    }


def _validate_contracts(repository_root: Path) -> dict[str, object]:
    registry = RegistryLoader(repository_root)
    skill_loader = SkillLoader(registry)
    entries = registry.load()
    for name in entries:
        skill_loader.load_registered(name)
    project_loader = ProjectLoader(repository_root, registry_loader=registry)
    project_ids = project_loader.list_project_ids()
    for project_id in project_ids:
        project_loader.load(project_id)
    return {
        "valid": True,
        "skills": list(entries),
        "projects": list(project_ids),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list-skills":
            payload = _list_skills(args.repository_root)
        elif args.command == "validate-contracts":
            payload = _validate_contracts(args.repository_root)
        elif args.command == "run":
            repository_root = args.repository_root.resolve()
            result = AgentRuntime(repository_root).run(
                task=f"Run registered Skill {args.skill}",
                skill_name=args.skill,
                project_id=args.project,
                inputs=_parse_inputs(args.input),
                run_root=args.run_root or repository_root / "runs",
                capabilities={},
            )
            payload = result.to_dict()
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if result.succeeded else 1
        else:
            validation = ValidatorEngine().validate_trace_file(args.trace)
            payload = {"valid": validation.valid, "errors": list(validation.errors)}
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if validation.valid else 1
    except AgentRuntimeError as exc:
        payload = {"valid": False, "code": exc.code, "error": exc.message}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
