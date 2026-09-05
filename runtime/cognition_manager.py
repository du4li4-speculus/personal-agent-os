"""Load registered reasoning protocols and invoke the Cognition capability."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

from .capabilities import CapabilitySet
from .contract_validator import ContractValidator
from .models import (
    AgentRuntimeError,
    CognitionPhaseResult,
    CognitionPolicy,
    CognitionProtocol,
    DependencyError,
)


COGNITION_CAPABILITY = "cognition.execute"
PHASE_TO_STATE = {
    "prepare": "COGNITION_PREPARE",
    "critique": "COGNITION_CRITIQUE",
    "memory_review": "MEMORY_REVIEW",
}
VALID_MODES = {"disabled", "optional", "required"}
PREPARE_PROPOSAL_FIELDS = {
    "framing",
    "expansion",
    "criteria",
    "decision_support",
}


class CognitionManager:
    """Execute domain-neutral Cognition phases through one typed capability port."""

    def __init__(
        self,
        repository_root: Path,
        capabilities: CapabilitySet,
        *,
        provider_declared: bool,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.cognition_root = (self.repository_root / "cognition").resolve()
        self.registry_path = self.cognition_root / "protocol_registry.yaml"
        self.contract_validator = ContractValidator(self.repository_root)
        self.capabilities = capabilities
        self.provider_declared = provider_declared
        self._protocols: Mapping[str, Mapping[str, Any]] | None = None

    @staticmethod
    def resolve_policy(*, skill_mode: str, project_mode: str) -> CognitionPolicy:
        if skill_mode not in VALID_MODES or project_mode not in VALID_MODES:
            raise AgentRuntimeError(
                "Cognition policy contains an unsupported mode",
                code="COGNITION_POLICY_INVALID",
            )
        if skill_mode == "required":
            effective = "required"
        elif skill_mode == "disabled" and project_mode == "required":
            raise AgentRuntimeError(
                "Project cannot require Cognition disabled by the Skill",
                code="COGNITION_POLICY_CONFLICT",
            )
        elif skill_mode == "disabled":
            effective = "disabled"
        elif project_mode == "required":
            effective = "required"
        elif project_mode == "disabled":
            effective = "disabled"
        else:
            effective = "optional"
        return CognitionPolicy(
            skill_mode=skill_mode,
            project_mode=project_mode,
            effective_mode=effective,
        )

    def run_phase(
        self,
        *,
        phase: str,
        protocol_ids: Sequence[str],
        policy: CognitionPolicy,
        context: Mapping[str, Any],
    ) -> CognitionPhaseResult:
        if phase not in PHASE_TO_STATE:
            raise AgentRuntimeError(
                f"Unsupported Cognition phase: {phase}",
                code="COGNITION_PHASE_INVALID",
            )
        selected = tuple(protocol_ids)
        state = PHASE_TO_STATE[phase]
        if policy.effective_mode == "disabled":
            return CognitionPhaseResult(
                phase=state,
                protocols=selected,
                effective_mode=policy.effective_mode,
                loaded=False,
                executed=False,
                validated=False,
                status="skipped",
                provider_outcome=None,
                changed_run_disposition=False,
                reason="policy_disabled",
            )

        if not selected:
            required = policy.effective_mode == "required"
            return CognitionPhaseResult(
                phase=state,
                protocols=(),
                effective_mode=policy.effective_mode,
                loaded=False,
                executed=False,
                validated=False,
                status="blocked" if required else "skipped",
                provider_outcome="protocol_missing" if required else None,
                changed_run_disposition=required,
                reason="protocol_required" if required else "no_protocol_selected",
                error_code="COGNITION_PROTOCOL_REQUIRED" if required else None,
            )

        try:
            protocols = self._load_protocols(selected, phase)
        except AgentRuntimeError:
            return CognitionPhaseResult(
                phase=state,
                protocols=selected,
                effective_mode=policy.effective_mode,
                loaded=False,
                executed=False,
                validated=False,
                status="blocked",
                provider_outcome="protocol_invalid",
                changed_run_disposition=True,
                reason="protocol_load_failed",
                error_code="COGNITION_PROTOCOL_INVALID",
            )

        provider = (
            self.capabilities.optional(COGNITION_CAPABILITY)
            if self.provider_declared
            else None
        )
        if provider is None:
            if policy.effective_mode == "required":
                return CognitionPhaseResult(
                    phase=state,
                    protocols=selected,
                    effective_mode=policy.effective_mode,
                    loaded=True,
                    executed=False,
                    validated=False,
                    status="blocked",
                    provider_outcome="provider_missing",
                    changed_run_disposition=True,
                    reason=(
                        "provider_required"
                        if self.provider_declared
                        else "provider_not_declared"
                    ),
                    error_code="COGNITION_PROVIDER_MISSING",
                )
            return CognitionPhaseResult(
                phase=state,
                protocols=selected,
                effective_mode=policy.effective_mode,
                loaded=True,
                executed=False,
                validated=False,
                status="skipped",
                provider_outcome=None,
                changed_run_disposition=False,
                reason=(
                    "provider_unavailable"
                    if self.provider_declared
                    else "provider_not_declared"
                ),
            )

        request = {
            "schema_version": "1.0",
            "phase": phase,
            "protocols": [
                {"id": protocol.protocol_id, "content": protocol.content}
                for protocol in protocols
            ],
            "context": dict(context),
        }
        try:
            response = provider(COGNITION_CAPABILITY, request)
        except Exception:
            return CognitionPhaseResult(
                phase=state,
                protocols=selected,
                effective_mode=policy.effective_mode,
                loaded=True,
                executed=True,
                validated=False,
                status="blocked",
                provider_outcome="provider_error",
                changed_run_disposition=True,
                reason="provider_failed",
                error_code="COGNITION_PROVIDER_FAILED",
            )
        return self._validate_response(
            phase=phase,
            state=state,
            selected=selected,
            effective_mode=policy.effective_mode,
            response=response,
        )

    def validate_registry(self) -> tuple[str, ...]:
        """Validate every registered protocol file without executing Cognition."""

        registry = self._load_registry()
        for protocol_id, raw in registry.items():
            self._load_protocols((protocol_id,), raw["phases"][0])
        return tuple(registry)

    def validate_selection(
        self, *, phase: str, protocol_ids: Sequence[str]
    ) -> tuple[str, ...]:
        """Validate one Skill selection without invoking a provider."""

        if phase not in PHASE_TO_STATE:
            raise AgentRuntimeError(
                f"Unsupported Cognition phase: {phase}",
                code="COGNITION_PHASE_INVALID",
            )
        selected = tuple(protocol_ids)
        self._load_protocols(selected, phase)
        return selected

    def _load_protocols(
        self, protocol_ids: tuple[str, ...], phase: str
    ) -> tuple[CognitionProtocol, ...]:
        registry = self._load_registry()
        loaded: list[CognitionProtocol] = []
        for protocol_id in protocol_ids:
            try:
                raw = registry[protocol_id]
            except KeyError as exc:
                raise AgentRuntimeError(
                    f"Cognition protocol is not registered: {protocol_id}",
                    code="COGNITION_PROTOCOL_NOT_FOUND",
                ) from exc
            if phase not in raw["phases"]:
                raise AgentRuntimeError(
                    f"Cognition protocol {protocol_id} is not valid for {phase}",
                    code="COGNITION_PROTOCOL_PHASE_INVALID",
                )
            path = (self.cognition_root / raw["path"]).resolve()
            try:
                path.relative_to(self.cognition_root)
            except ValueError as exc:
                raise AgentRuntimeError(
                    f"Cognition protocol escapes its root: {protocol_id}",
                    code="COGNITION_PROTOCOL_PATH_ESCAPE",
                ) from exc
            if not path.is_file():
                raise AgentRuntimeError(
                    f"Cognition protocol file does not exist: {protocol_id}",
                    code="COGNITION_PROTOCOL_MISSING",
                )
            try:
                content = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise AgentRuntimeError(
                    f"Unable to read Cognition protocol: {protocol_id}",
                    code="COGNITION_PROTOCOL_UNREADABLE",
                ) from exc
            loaded.append(
                CognitionProtocol(
                    protocol_id=protocol_id,
                    phases=tuple(raw["phases"]),
                    content=content,
                )
            )
        return tuple(loaded)

    def _load_registry(self) -> Mapping[str, Mapping[str, Any]]:
        if self._protocols is not None:
            return self._protocols
        if yaml is None:
            raise DependencyError(
                "PyYAML is required to load Cognition protocols"
            ) from _YAML_IMPORT_ERROR
        try:
            document = yaml.safe_load(self.registry_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AgentRuntimeError(
                f"Unable to read Cognition protocol registry: {self.registry_path}",
                code="COGNITION_REGISTRY_INVALID",
            ) from exc
        violations = self.contract_validator.validate(
            document,
            self.repository_root
            / "contracts"
            / "cognition-protocol-registry.schema.json",
        )
        if violations:
            violation = violations[0]
            raise AgentRuntimeError(
                "Cognition protocol registry violation at "
                f"{violation.path} ({violation.keyword}): {violation.message}",
                code="COGNITION_REGISTRY_INVALID",
            )
        self._protocols = MappingProxyType(
            {
                protocol_id: MappingProxyType(dict(raw))
                for protocol_id, raw in document["protocols"].items()
            }
        )
        return self._protocols

    @staticmethod
    def _validate_response(
        *,
        phase: str,
        state: str,
        selected: tuple[str, ...],
        effective_mode: str,
        response: Mapping[str, Any],
    ) -> CognitionPhaseResult:
        invalid = not isinstance(response, Mapping)
        outcome = response.get("outcome") if not invalid else None
        proposal_fields: tuple[str, ...] = ()
        candidate_payload: Mapping[str, Any] | None = None

        if phase == "prepare" and not invalid:
            invalid = set(response) - {"outcome", "proposal"} != set()
            proposal = response.get("proposal", {})
            invalid = invalid or outcome != "pass" or not isinstance(proposal, Mapping)
            if isinstance(proposal, Mapping):
                proposal_keys = tuple(proposal)
                keys_are_strings = all(
                    isinstance(key, str) for key in proposal_keys
                )
                invalid = invalid or not keys_are_strings
                if keys_are_strings:
                    invalid = invalid or bool(
                        set(proposal_keys) - PREPARE_PROPOSAL_FIELDS
                    )
                    proposal_fields = tuple(sorted(proposal_keys))
        elif phase == "critique" and not invalid:
            invalid = set(response) != {"outcome"} or outcome not in {
                "pass",
                "blocked",
                "review_required",
            }
        elif phase == "memory_review" and not invalid:
            invalid = set(response) - {"outcome", "memory_candidate"} != set()
            invalid = invalid or outcome not in {"no_candidate", "candidate"}
            if outcome == "candidate":
                candidate = response.get("memory_candidate")
                invalid = invalid or not isinstance(candidate, Mapping)
                if isinstance(candidate, Mapping):
                    candidate_payload = dict(candidate)
            else:
                invalid = invalid or "memory_candidate" in response

        if invalid:
            return CognitionPhaseResult(
                phase=state,
                protocols=selected,
                effective_mode=effective_mode,
                loaded=True,
                executed=True,
                validated=False,
                status="blocked",
                provider_outcome="invalid_response",
                changed_run_disposition=True,
                reason="provider_result_invalid",
                error_code="COGNITION_RESULT_INVALID",
            )

        status = "executed"
        error_code = None
        changed = False
        if phase == "critique" and outcome == "blocked":
            status = "blocked"
            error_code = "COGNITION_BLOCKED"
            changed = True
        elif phase == "critique" and outcome == "review_required":
            status = "review_required"
            error_code = "COGNITION_REVIEW_REQUIRED"
            changed = True
        return CognitionPhaseResult(
            phase=state,
            protocols=selected,
            effective_mode=effective_mode,
            loaded=True,
            executed=True,
            validated=True,
            status=status,
            provider_outcome=str(outcome),
            changed_run_disposition=changed,
            proposal_fields=proposal_fields,
            candidate_payload=candidate_payload,
            error_code=error_code,
        )
