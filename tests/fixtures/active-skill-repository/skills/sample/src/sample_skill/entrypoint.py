"""Registered fixture entrypoint used only by Runtime boundary tests."""

from pathlib import Path

from runtime.models import SkillExecutionResult


def execute(context, skill, capabilities):
    context.output_dir.mkdir(parents=True, exist_ok=True)
    (context.output_dir / "execution-started.txt").write_text(
        "fixture entrypoint started\n", encoding="utf-8"
    )
    result_path = context.output_dir / "result.txt"
    result_path.write_text(
        f"skill={skill.name}\nproject={context.project_id}\n", encoding="utf-8"
    )

    metadata = {}
    provider = capabilities.optional("fixture.echo")
    if provider is not None:
        metadata["fixture.echo"] = dict(
            provider("fixture.echo", {"value": "registered-entrypoint"})
        )

    return SkillExecutionResult(
        intermediate_artifacts={},
        artifacts={"result.txt": Path("result.txt")},
        metadata=metadata,
    )
