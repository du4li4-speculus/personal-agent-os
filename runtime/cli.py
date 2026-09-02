"""Command-line entry points for exercising and validating the runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .models import LoadedSkill, RunContext
from .runner import AgentRuntime
from .validator_engine import ValidatorEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal Agent OS runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser(
        "run-demo", help="run a deterministic fixture adapter through the runtime"
    )
    demo.add_argument("--skill", default="toefl-writing-grader")
    demo.add_argument("--output-dir", type=Path, required=True)
    demo.add_argument("--repository-root", type=Path, default=Path.cwd())

    validate = subparsers.add_parser(
        "validate-trace", help="validate a persisted successful execution trace"
    )
    validate.add_argument("--trace", type=Path, required=True)
    return parser


def demo_executor(context: RunContext, skill: LoadedSkill) -> dict[str, Path]:
    """Write explicitly labeled fixture files, never real assessment output."""

    artifacts: dict[str, Path] = {}
    for output_name in skill.outputs:
        output_path = context.output_dir / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "PERSONAL AGENT OS RUNTIME DEMO FIXTURE\n"
            f"skill={skill.name}\n"
            f"version={skill.version}\n"
            f"artifact={output_name}\n",
            encoding="utf-8",
        )
        artifacts[output_name] = Path(output_name)
    return artifacts


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run-demo":
        runtime = AgentRuntime(args.repository_root)
        result = runtime.run(
            task="Runtime contract smoke test; fixture artifacts only",
            skill_name=args.skill,
            executor=demo_executor,
            output_dir=args.output_dir,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
        return 0 if result.succeeded else 1

    validation = ValidatorEngine().validate_trace_file(args.trace)
    print(
        json.dumps(
            {"valid": validation.valid, "errors": list(validation.errors)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if validation.valid else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
