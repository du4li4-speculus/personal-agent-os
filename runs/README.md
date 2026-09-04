# Runs

Every new run instance is isolated under `runs/<project-id>/<run-id>/` with these owned directories:

- `input/` — staged copies and a hash manifest; original filesystem paths are not recorded.
- `work/` — intermediate artifacts declared by the Skill.
- `artifacts/` — final declared artifacts.
- `trace/` — the execution trace.
- `memory/` — at most one proposed `memory_candidate.json`.

Run contents are ignored because they may contain sensitive instance data. Runtime paths must resolve inside the current run before any write is accepted.
