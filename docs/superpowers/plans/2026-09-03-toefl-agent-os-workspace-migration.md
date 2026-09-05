# TOEFL-Agent-OS Workspace Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/` as the canonical TOEFL workspace and migrate the existing TOEFL records, Agent OS runtime, writing-grader logic, and trial outputs into the requested layout.

**Architecture:** Keep the existing TOEFL workspace files as source records and create a new canonical destination with explicit inbox, intervention, skill, corpus, and output boundaries. Preserve the current Agent OS control plane (`core`, `registry`, `runtime`, `tests`, and docs) so the migrated project remains executable. Merge the current Agent OS writing skill with the accumulated writing-domain package from `speaking-assessment-v1`, keeping the Agent OS entrypoint authoritative and the older package traceable under skill references.

**Tech Stack:** Filesystem copy with `rsync`/`ditto`, Python 3.9 validation, existing TOEFL Writing skill schemas/tests, SHA-256 manifest, and read-only source preservation.

**Spec:** User-requested `TOEFL-Agent-OS/` layout and the existing Agent OS/TOEFL Writing skill contracts in `personal-agent-os/` and `speaking-assessment-v1/`.

## Global Constraints

- Do not migrate unrelated pet projects from the New project workspace.
- Do not delete or overwrite the original source records; the first migration is copy-and-verify.
- Do not modify Agent OS runtime behavior during this filesystem migration.
- Keep the current Agent OS writing skill entrypoint authoritative; preserve older writing logic as traceable source material.
- Preserve exact filenames and source bytes for student records and generated outputs.
- Do not treat the empty `AnnotationAuthorStorage` in a Pages package as proof that annotations do not exist.

---

### Task 1: Create the destination workspace boundary

**Files:**
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/00_Grading-Inbox/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/01_Intervention-Inbox/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/skills/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/corpus/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/outputs/`

**Interfaces:**
- Consumes: Existing target workspace `/Users/aumarb/Desktop/AI工作区/托福工作区/`.
- Produces: A destination root with the five requested data/code boundaries; control-plane directories may be added beside them to preserve Agent OS execution.

- [ ] Create the destination root and requested directories without touching the existing `学生写作和批改`, `课堂记录`, or `造句错误` directories.
- [ ] Add control-plane directories `core/`, `registry/`, `runtime/`, `tests/`, and `docs/` only as required by the migrated Agent OS project.
- [ ] Record the destination path and initial directory list in the migration manifest.

### Task 2: Migrate and classify existing TOEFL records

**Files:**
- Source: `/Users/aumarb/Desktop/AI工作区/托福工作区/学生写作和批改/`
- Source: `/Users/aumarb/Desktop/AI工作区/托福工作区/课堂记录/`
- Source: `/Users/aumarb/Desktop/AI工作区/托福工作区/造句错误/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/00_Grading-Inbox/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/01_Intervention-Inbox/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/outputs/`

**Interfaces:**
- Consumes: 665 non-system files from the existing mixed student folder, four `批改_*.docx` records, the sentence-error folder, and the class-record folder.
- Produces: Student submissions in `00_Grading-Inbox`, class/correction/homework records in `01_Intervention-Inbox`, and reports/summaries in `outputs`.

- [ ] Classify `学生写作和批改` files by basename: `家长简报_*`, `学生简报_*`, `批量评估*`, and HTML/JSON reports go to `outputs`; `批改_*` goes to `01_Intervention-Inbox`; all other student source files go to `00_Grading-Inbox`.
- [ ] Copy `造句错误` into `01_Intervention-Inbox/sentence-errors/` and `课堂记录` into `01_Intervention-Inbox/class-notes/`, preserving filenames and the empty class-notes state.
- [ ] Ignore only macOS `.DS_Store` files; do not silently omit any substantive record.
- [ ] Compare source and destination file counts, byte totals, and SHA-256 hashes before recording the task as complete.

### Task 3: Migrate the Agent OS control plane and writing skill

**Files:**
- Source: `/Users/aumarb/Documents/ChatGPT/New project/personal-agent-os/{README.md,requirements.txt,core,registry,runtime,tests,docs}`
- Source: `/Users/aumarb/Documents/ChatGPT/New project/personal-agent-os/skills/toefl-writing-grader/`
- Source: `/Users/aumarb/Documents/ChatGPT/New project/speaking-assessment-v1/skills/toefl-writing-grader/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/skills/toefl-writing-grader/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/skills/teaching-loop-manager/`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/corpus/README.md`

**Interfaces:**
- Consumes: Current Agent OS contracts plus accumulated TOEFL Writing rules, scripts, templates, tests, schemas, and historical references.
- Produces: An executable TOEFL-Agent-OS control plane; an active `toefl-writing-grader` skill; a traceable teaching-loop skill extracted from the existing diagnostic/learning logic; and a 2026 TOEFL rulepack corpus.

- [ ] Copy the Agent OS control plane without its nested `.git` metadata or unrelated generated assets.
- [ ] Copy the current Agent OS `toefl-writing-grader` package as the destination base, excluding instance-specific `output/` data.
- [ ] Copy the `speaking-assessment-v1` writing `rules/`, `scripts/`, `agents/`, and non-conflicting templates into the active skill; preserve conflicting source files under `references/source-speaking-assessment-v1/` rather than overwriting the active entrypoint or schemas.
- [ ] Build `teaching-loop-manager` from the existing `learning_loop.py`, `diagnostic_engine.py`, `profile_engine.py`, `coverage_engine.py`, and their governing rules; do not invent a new scoring rule.
- [ ] Create a corpus README that defines what belongs in the corpus and records that the source repository's `rulepacks/toefl_2026` is a speaking rulepack, so it is not misclassified as TOEFL Writing corpus data.
- [ ] Verify that `core/agent.md`, `core/workflow.md`, and `runtime/state_machine.yaml` remain byte-identical to their source copies; update the destination registry only by adding the migrated `teaching-loop-manager` entry.

### Task 4: Migrate trial and generated outputs

**Files:**
- Source: `/Users/aumarb/Documents/ChatGPT/New project/personal-agent-os/skills/toefl-writing-grader/output/831_白雪_试批/`
- Source: Existing target report files classified in Task 2.
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/outputs/831_白雪_试批/`

**Interfaces:**
- Consumes: `source_bundle.json`, `evidence.json`, `assessment.json`, `diagnosis.json`, `learning_loop.json`, `validation_record.json`, teacher dashboard data, and the student/parent PDFs.
- Produces: A canonical output archive with the current 831 trial linked to its source records and validation state.

- [ ] Copy the complete 831 trial directory into `outputs/831_白雪_试批/`, separating its `data/` and `pdf/` subdirectories unchanged.
- [ ] Copy all legacy student/parent reports and summary reports into `outputs/legacy-reports/` without renaming or overwriting duplicate basenames.
- [ ] Keep the 831 validation state `blocked` because `白雪` and `Belly` conflict; do not silently resolve the identity.

### Task 5: Validate migration and publish manifest

**Files:**
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/MIGRATION_MANIFEST.md`
- Create: `/Users/aumarb/Desktop/AI工作区/托福工作区/TOEFL-Agent-OS/README.md`

**Interfaces:**
- Consumes: Destination tree, source/destination inventories, SHA-256 comparisons, Agent OS regression tests, and output validation.
- Produces: A human-readable canonical workspace guide and an auditable migration record.

- [ ] Run `PYTHONPATH=... python3 -B -m unittest discover -s tests` from the migrated Agent OS root.
- [ ] Validate JSON/YAML parsing for runtime, registry, skill schemas, and the 831 output data.
- [ ] Verify that every requested top-level directory exists, the teaching-loop skill exists, and no pet-project directory was copied.
- [ ] Write counts, source paths, destination paths, excluded system files, and verification results into `MIGRATION_MANIFEST.md`.
- [ ] Leave the original source directories intact and report the canonical destination path.
