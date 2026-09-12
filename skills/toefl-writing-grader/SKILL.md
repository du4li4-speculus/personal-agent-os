---
name: toefl-writing-grader
description: Normalize, inspect, or grade TOEFL Writing responses when a student response is provided, or when developing and validating the TOEFL grading workflow.
agent_created: true
---

# TOEFL Writing Grader

Use this Skill as the Controller entrypoint for TOEFL Write an Email and Write for an Academic Discussion.

## Start with capability status

Read [references/current-capabilities.md](references/current-capabilities.md) before choosing a stage. Execute only stages marked available. A planned stage is not a completion gate for an available stage, and its absence must not cause waiting.

## Route by requested stage

- For input normalization, provenance, attachment parsing, or evidence readiness, read [references/input-and-evidence-contract.md](references/input-and-evidence-contract.md).
- For scoring, rubric interpretation, score synchronization, or assessment review, read [references/scoring-contract.md](references/scoring-contract.md).
- For student, parent, or teacher report content, read [references/report-content-contract.md](references/report-content-contract.md). Presentation styling belongs to the report-design workflow, not this scoring Skill.
- For future stages and activation dependencies, read [references/roadmap.md](references/roadmap.md) only when planning or implementing those stages.

Load only the references needed for the current request.

## Controller invariants

- Never assess without traceable source evidence.
- Preserve genuine truncation and missing prompt material; do not reconstruct student text from memory or analogy.
- Teacher judgment may override AI diagnosis. Record the override as evidence for later review; do not silently rewrite rubric rules.
- Validate the stages and artifacts emitted in the current run. Do not create optional reports, caches, archives, or memory records solely to satisfy a check.
- Complete every available stage required by the request. If a required stage is unavailable, report that boundary once and return all completed upstream artifacts without waiting.
