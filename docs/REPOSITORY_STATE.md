# Repository State for Agent OS v0.3+

## Publication snapshot

- Verified: 2026-09-05, Asia/Shanghai
- Repository: `du4li4-speculus/personal-agent-os`
- Integration branch: `codex/agent-os-v0.3-plus`
- Local foundation branch tip at integration start: `ce807686bddd470b7e647642f3ee52ea7c67ee66`
- Merged GitHub `main` SHA: `31763539884aaba4a8b24f0065a50d432d78b89b`
- Reconciliation merge: `da0a3cfa0e84119c15f25cab51d9e581a4a6f81b`
- Test suite: 86 tests passing
- Registry status: no production-active Skills; `toefl-writing-grader` 2.0.0 is `development`
- Publication commit: `docs: publish agent os architecture v0.3+` (this commit)

The integration branch preserves both the local executable Runtime lineage and the verified GitHub Cognition/governance lineage. No rebase, force update, or history rewrite was used.

## Actual v0.3+ integration sequence

This is the actual first-parent Task sequence, including the separately reviewed Task 7 lifecycle reconciliation amendment. It supersedes the originally planned sequence as a statement of what happened; historical plans remain unchanged under `docs/PLAN_STATUS.md`.

| Order | Task | Commit | Result |
| --- | --- | --- | --- |
| 1 | Task 1 | `fe3abd9` `chore: preserve current agent os working state` | Preserved the complete source state while excluding local run data. |
| 2 | Task 2 | `da0a3cf` `merge: reconcile github architecture with local runtime` | Merged GitHub `main` at `3176353` with the local Runtime lineage. |
| 3 | Task 3 | `625d5e4` `docs: establish agent os governance contracts` | Established five policy owners and six ADRs. |
| 4 | Task 4 | `47f2628` `feat: define agent os machine contracts` | Added versioned Registry, Skill, Project, Run, Memory Candidate, and Agent-role contracts. |
| 5 | Task 5 | `d6886d9` `feat: execute registered skill entrypoints` | Enforced safe Registry-resolved Skill-local entrypoints and typed capability ports. |
| 6 | Task 6 | `0490989` `feat: isolate project run and memory data` | Established Project, Run, input-staging, and candidate-only Memory boundaries. |
| 7 | Task 7 | `2dd24fe` `feat: integrate cognition lifecycle hooks` | Integrated policy-controlled Prepare, Critique, and Memory Review hooks. |
| 8 | Task 7 amendment | `57e95b5` `fix: reconcile task 7 lifecycle ordering` | Canonicalized the implemented lifecycle and strengthened complete transition validation. |
| 9 | Task 8 | `daca115` `test: enforce the TOEFL skill boundary` | Tested implemented input/evidence stages and preserved truthful development status. |
| 10 | Task 9 | `ba3cc8b` `test: enforce agent os architecture boundaries` | Added real-repository invariants and CI enforcement. |
| 11 | Task 10 | this commit, `docs: publish agent os architecture v0.3+` | Published documentation that matches tested behavior and current readiness. |

The merged GitHub lineage ends at `3176353` (`Add registry policy for capability boundaries`). The local Runtime foundation immediately before Task 1 consists of `ce9c8cf` (`docs: specify agent runtime foundation`) and `ce80768` (`feat: implement executable agent runtime`).

## Verified architecture state

- The one-way authority chain and distinction from source dependencies are canonical in `docs/ARCHITECTURE_BOUNDARIES.md`.
- Five governance policies under `docs/policies/` and six accepted ADRs under `docs/adr/` own architecture decisions.
- Machine contracts and cross-document validation cover Registry, Skill, Project, Run, Memory Candidate, and Agent-role documents.
- Production Runtime accepts no caller-supplied domain executor and imports no TOEFL/domain package directly.
- Safe entrypoint resolution rejects absolute, traversal, symlink-escape, and realpath-escape paths and cleans temporary import state.
- New run-instance data is contained under `runs/<project-id>/<run-id>/`; Runtime has no persistent Memory promotion API.
- Cognition protocol selection/loading, provider execution, skipping, blocking, review requirements, and validation remain distinct trace facts.
- The reconciled lifecycle is `LOAD_SKILL -> RUNTIME_CHECK -> COGNITION_PREPARE -> EXECUTE -> ARTIFACT -> COGNITION_CRITIQUE -> VALIDATE -> MEMORY_REVIEW -> DELIVER`.
- `ARTIFACT` is structural admission only. Critique is references-only, and blocked or review-required output is non-deliverable.

## Skill truth

The Registry contains one Skill:

- `toefl-writing-grader` 2.0.0 — `development`

Implemented and tested TOEFL stages are limited to input normalization, provenance preservation, evidence extraction, assessment-readiness gating, and source/evidence schema validation. There is no production entrypoint and no assessment, diagnosis, learning-loop, PDF, or dashboard execution. Activation remains governed by `docs/TOEFL_SKILL_ACTIVATION_CRITERIA.md`.

## Data and working-tree status

- `runs/.gitignore` ignores run-instance content while retaining only `runs/.gitignore` and `runs/README.md` as tracked scaffolding.
- `.gitignore` ignores `skills/*/output/`, including the original legacy TOEFL output.
- `runs/toefl-writing/legacy-831-baixue-trial/` is an ignored preservation copy. Read-only comparison on 2026-09-05 found its 12 files byte-identical to the original legacy output; the original was not renamed, deleted, or modified.
- No run-instance file or Skill output file is tracked.
- `docs/reviews/` remains untracked and is intentionally outside the Task 10 publication commit.
- Persistent Memory scaffolding under `memory/global/`, `memory/projects/`, and `memory/skills/` is tracked, but Runtime-created candidates are run-local and do not constitute persistent learning.

## Final verification contract

The publication boundary is verified with:

```bash
python3 -m runtime.cli validate-contracts
python3 -m unittest discover -s tests -v
git diff --check
git status --short
```

CI additionally runs the dedicated architecture-boundary test module before the full suite. Its final `git diff --check` invocation checks the diff present in the checkout and is not a historical-whitespace audit.

## Known limitations and follow-on boundary

- There is no production-active Skill, so the Runtime control plane is executable but no repository domain workflow is production-ready.
- The repository does not ship a model- or vendor-specific Cognition provider; protocol loading alone is not provider execution.
- Cognition Critique is references-only. Content inspection requires a new or superseding ADR and a bounded inspection capability.
- Runtime can create a proposed run-local Memory Candidate but cannot promote or write persistent Memory.
- TOEFL assessment, diagnosis, learning-loop execution, PDF rendering, dashboard generation, and composite entrypoint work remain outside v0.3+.

No push, merge to `main`, pull request, tag, release, domain completion, provider integration, or persistent-Memory promotion is part of this publication task.
