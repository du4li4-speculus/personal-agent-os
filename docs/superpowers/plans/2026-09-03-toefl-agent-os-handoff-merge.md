# TOEFL Agent OS Handoff Merge Plan

## Goal

Merge the 2026-09-03 Desktop merge bundle into the existing TOEFL-Agent-OS workspace while keeping the stable Desktop Writing Grader implementation authoritative and preserving the Handoff's frozen Corpus, identity, task-independence, Validation, and Teaching Loop rules.

## Steps

1. Read and inventory the existing Agent OS contracts, Writing Grader, Teaching Loop scaffold, and Handoff bundle.
2. Copy the three Corpus packages into versioned immutable locations: `corpus/snapshots/Pilot41-v0.2/`, `corpus/validation/Round5/`, and `corpus/holdout/Blind18-v0.1/`.
3. Copy Teaching Loop ingestion v0.2 into a versioned integration directory and expose it through a versioned active script name without overwriting current scripts.
4. Append the frozen Handoff rules to the existing Writing Grader and Teaching Loop skill contracts; record every same-name or semantic overlap in `MERGE_CONFLICTS.md`.
5. Create/update root `AGENTS.md`, `PROJECT_STATE.md`, and Corpus routing documentation.
6. Run Agent OS tests, historical Writing Grader tests, Writing Grader input/evidence smoke coverage, and Teaching Loop v0.2 acceptance plus real filename parsing smoke coverage.
7. Verify copied package hashes, output manifests, and final status before delivery.

## Constraints

- Do not delete source material or overwrite a different existing file.
- Do not redesign TOEFL scoring or claim Blind18 is formal Corpus data.
- Do not infer diagnosis, completion, causality, or effectiveness from filenames or reports alone.
- Keep original filenames and source hashes; represent identity aliases as observed and canonical values.
