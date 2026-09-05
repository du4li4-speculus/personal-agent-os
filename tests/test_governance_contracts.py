from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_ROOT = REPO_ROOT / "docs" / "policies"
ADR_ROOT = REPO_ROOT / "docs" / "adr"

POLICIES = (
    "MEMORY_POLICY.md",
    "RUNTIME_POLICY.md",
    "AGENT_ROLE_POLICY.md",
    "EXTENSION_POLICY.md",
    "PROJECT_BOUNDARY_POLICY.md",
)
POLICY_SECTIONS = (
    "## Owner",
    "## Owns",
    "## Must not own",
    "## Invariants",
    "## Enforcement",
    "## Change process",
)
ADRS = (
    "0001-reconcile-repository-states.md",
    "0002-enforce-one-way-layer-ownership.md",
    "0003-resolve-skills-through-registry-entrypoints.md",
    "0004-isolate-project-run-and-memory-data.md",
    "0005-integrate-cognition-lifecycle.md",
    "0006-govern-agent-roles.md",
)
ADR_SECTIONS = (
    "## Status",
    "## Context",
    "## Expansion",
    "## Critique",
    "## Decision",
    "## Rejected alternatives",
    "## Consequences",
    "## Future changes enabled",
)
AUTHORITY_CHAIN = (
    "Core -> Cognition -> Runtime Control Plane -> Registry -> Skill -> "
    "Project -> Artifacts -> Memory Candidate"
)


class GovernanceContractTests(unittest.TestCase):
    def test_every_governance_policy_has_one_contract_shape(self) -> None:
        actual = tuple(sorted(path.name for path in POLICY_ROOT.glob("*.md")))
        self.assertEqual(actual, tuple(sorted(POLICIES)))

        for name in POLICIES:
            text = (POLICY_ROOT / name).read_text(encoding="utf-8")
            for heading in POLICY_SECTIONS:
                self.assertIn(heading, text, f"{name} is missing {heading}")

    def test_every_v03_adr_records_required_cognitive_process(self) -> None:
        actual = tuple(
            sorted(path.name for path in ADR_ROOT.glob("000[1-6]-*.md"))
        )
        self.assertEqual(actual, tuple(sorted(ADRS)))

        for name in ADRS:
            text = (ADR_ROOT / name).read_text(encoding="utf-8")
            for heading in ADR_SECTIONS:
                self.assertIn(heading, text, f"{name} is missing {heading}")

    def test_architecture_boundary_publishes_one_authority_chain(self) -> None:
        text = (REPO_ROOT / "docs" / "ARCHITECTURE_BOUNDARIES.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(AUTHORITY_CHAIN, text)
        self.assertIn("ownership and execution-authority flow", text)
        self.assertIn("source-code dependency", text)

    def test_core_links_to_canonical_policies(self) -> None:
        agent = (REPO_ROOT / "core" / "agent.md").read_text(encoding="utf-8")
        workflow = (REPO_ROOT / "core" / "workflow.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("docs/policies/AGENT_ROLE_POLICY.md", agent)
        self.assertIn("docs/policies/RUNTIME_POLICY.md", workflow)
        self.assertIn("docs/policies/MEMORY_POLICY.md", workflow)

    def test_registry_policy_owns_discovery_only(self) -> None:
        text = (REPO_ROOT / "docs" / "REGISTRY_POLICY.md").read_text(
            encoding="utf-8"
        )
        for term in ("identity", "version", "status", "manifest", "entrypoint"):
            self.assertIn(term, text.lower())
        for excluded_owner in (
            "reasoning protocols",
            "persistent memory",
            "user preferences",
            "architecture rules",
        ):
            self.assertIn(excluded_owner, text.lower())


if __name__ == "__main__":
    unittest.main()
