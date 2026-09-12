# Current Capabilities

This table is the execution source of truth for the TOEFL Writing Grader. Repository rules and templates describe intent but do not prove that a stage is executable.

| Stage | Status | Current boundary |
| --- | --- | --- |
| Input normalization | available | Produces the normalized source bundle from supported inputs. |
| Provenance preservation | available | Records source identity and extraction provenance. |
| Evidence extraction | available | Produces traceable evidence and records truncation or parsing gaps. |
| Assessment-readiness gate | available | Determines whether the evidence is sufficient to assess. |
| Source/evidence schema validation | available | Validates implemented source and evidence contracts. |
| Rubric-based scoring runtime | planned | Rules exist, but there is no registered composite execution path. |
| Diagnosis and learning loop | planned | Contracts may exist; runtime execution is not active. |
| Student report rendering | planned | Content and design requirements do not constitute an implementation. |
| Parent report rendering | planned | Content and design requirements do not constitute an implementation. |
| Teacher/controller dashboard | planned | No complete rendering path is active. |
| End-to-end domain validation | planned | Activate only after all required upstream stages are executable. |

When implementation status changes, update this file in the same change that provides and validates the executable path.
