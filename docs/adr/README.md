# Architecture Decision Records

This directory is the canonical index of accepted Agent OS architecture decisions. ADRs are immutable records of why a boundary was chosen; a later decision changes status by adding a new ADR or explicitly superseding an existing one.

| ADR | Status | Decision |
| --- | --- | --- |
| [ADR-0001](0001-reconcile-repository-states.md) | Accepted | Preserve local source, then merge verified GitHub history without destructive reconciliation |
| [ADR-0002](0002-enforce-one-way-layer-ownership.md) | Accepted | Use one authority chain and distinguish it from source-code imports |
| [ADR-0003](0003-resolve-skills-through-registry-entrypoints.md) | Accepted | Resolve active Skills through validated Registry entrypoints |
| [ADR-0004](0004-isolate-project-run-and-memory-data.md) | Accepted | Separate Project configuration, run instances, persistent Memory, and run-local candidates |
| [ADR-0005](0005-integrate-cognition-lifecycle.md) | Accepted | Add explicit, truthfully traced Cognition hooks |
| [ADR-0006](0006-govern-agent-roles.md) | Accepted | Define Agents as evaluated roles rather than knowledge containers |

## Architecture change gate

Before an architecture-changing commit:

1. Identify the ADR that governs the boundary.
2. Apply Expansion, Critique, and Decision against current evidence.
3. Amend an unshared proposed record or add a new superseding ADR when the accepted boundary changes.
4. Stop before implementation if the change contradicts an accepted ADR and lacks explicit repository-owner approval.

The current implementation sequence and checkpoint are defined in `docs/superpowers/plans/2026-09-04-agent-os-architecture-upgrade-v0.3-plus.md`.
