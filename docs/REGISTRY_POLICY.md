# Registry Policy v0.3+

## Purpose

Make Registry the single discovery authority for executable capabilities without moving reasoning, policy, Memory, or domain implementation into Registry.

## Registry responsibility

Registry owns only:

- Skill identity;
- declared version;
- lifecycle status such as `active` or `development`;
- Skill-root and manifest resolution;
- entrypoint discovery for active Skills.

Registry metadata must be machine-verifiable against the resolved Skill manifest. Registry does not execute a Skill and does not validate domain semantics.

## Registration gate

A Registry entry requires:

- a stable identity and version;
- an owned Skill path and manifest path;
- defined inputs, intermediate outputs, final outputs, and validators in the manifest;
- required and optional capability declarations;
- tests appropriate to its advertised status.

An `active` Skill also requires a safe, resolvable entrypoint. A Skill without a complete entrypoint contract remains `development`; Registry must not compensate with a fake entrypoint or caller-supplied executor.

## Excluded ownership

Registry does not own or register:

- reasoning protocols;
- persistent Memory;
- user preferences;
- architecture rules;
- Core invariants;
- Project decisions;
- domain algorithms, scoring rules, or validators themselves.

These concerns remain in Cognition, Memory, Core, Project, or Skill according to `docs/ARCHITECTURE_BOUNDARIES.md`.

## Resolution boundary

Runtime may use Registry to locate a Skill manifest and entrypoint. Runtime then enforces generic path, capability, lifecycle, trace, artifact, and validation gates. Dynamic resolution does not permit Runtime source to import a domain Skill package directly.

## Version and status truth

- Registry and manifest versions match exactly.
- Status reflects executable readiness rather than documentation completeness.
- A version or status mismatch fails closed.
- Registry never silently selects, upgrades, or downgrades a Skill version.
- Repository checks validate every `active` Skill through the real Registry, manifest, and safe entrypoint loaders.
- A `development` Skill may omit an entrypoint or other executable stages, but Registry does not advertise it as an active capability.

`toefl-writing-grader` remains `development` until every gate in `docs/TOEFL_SKILL_ACTIVATION_CRITERIA.md` passes. Historical plans cannot change Registry truth; `docs/PLAN_STATUS.md` identifies their authority status.

## Change process

Changes to Registry ownership or status semantics require the Expansion, Critique, and Decision gate and an ADR. Adding an ordinary Skill entry that satisfies the existing contract follows `docs/policies/EXTENSION_POLICY.md` and does not redefine Registry policy.

## References

- `docs/policies/RUNTIME_POLICY.md`
- `docs/policies/EXTENSION_POLICY.md`
- `docs/adr/0003-resolve-skills-through-registry-entrypoints.md`
- `docs/PLAN_STATUS.md`
- `docs/TOEFL_SKILL_ACTIVATION_CRITERIA.md`
