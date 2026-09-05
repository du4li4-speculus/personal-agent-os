"""Opaque infrastructure capability ports exposed to registered Skills."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping, Optional

from .models import AgentRuntimeError, CapabilityProvider


class CapabilitySet:
    """Read-only provider lookup with no domain-specific interpretation."""

    def __init__(self, providers: Mapping[str, CapabilityProvider]) -> None:
        self._providers = MappingProxyType(dict(providers))

    def has(self, capability_id: str) -> bool:
        return capability_id in self._providers

    def require(self, capability_id: str) -> CapabilityProvider:
        provider = self._providers.get(capability_id)
        if provider is None:
            raise AgentRuntimeError(
                f"Required capability is unavailable: {capability_id}",
                code="RUNTIME_CAPABILITY_MISSING",
            )
        return provider

    def optional(self, capability_id: str) -> Optional[CapabilityProvider]:
        return self._providers.get(capability_id)
