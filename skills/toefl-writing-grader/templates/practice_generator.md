# Practice Generator

## Required input

- `diagnosis.json`: at least one issue with `evidence_ids`
- `priority`
- `ability_layer`
- `learning_loop.json`
- current task type (Email or Academic Discussion)

## Generation contract

Generate one short drill or timed rewrite task that can be checked in the next
evidence pass. Target an observed issue only; do not invent scoring rules or
require the student to change a position that is already valid.

## Required output

- `practice_task`: the concrete student task
- `target_ability`: `task_response`, `organization`, `language_control`, or `reasoning`
- `time_limit_minutes`: when applicable
- `success_signal`: an observable completion condition
- `validation_method`: evidence to collect and re-check next time
- `source_evidence_ids`: the evidence that triggered the task

## Valid success-signal examples

- Email: each task point has an independent information block and at least two concrete details.
- Academic: the claim, mechanism, and result are complete; the example supports the claim; no free-floating sentence is added.
- Language control: the next sample no longer contains the marked serious-error category, confirmed by new evidence.
