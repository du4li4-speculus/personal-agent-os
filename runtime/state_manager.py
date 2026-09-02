"""Validated state-machine controller for Agent OS runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Set

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

from .models import DependencyError, StateMachineError


class StateManager:
    """Keep one run on legal transitions from the configured state machine."""

    def __init__(
        self,
        states: Mapping[str, Mapping[str, Any]],
        *,
        initial_state: str = "CREATED",
        max_recovery_attempts: int = 1,
    ) -> None:
        self.states = dict(states)
        self._validate_states()
        if initial_state not in self.states:
            raise StateMachineError(f"Initial state is not defined: {initial_state}")
        self.current_state = initial_state
        self.max_recovery_attempts = max_recovery_attempts
        self.recovery_attempts = 0

    @classmethod
    def from_file(cls, path: Path) -> "StateManager":
        if yaml is None:
            raise DependencyError(
                "PyYAML is required to load Agent OS YAML contracts"
            ) from _YAML_IMPORT_ERROR
        if not path.is_file():
            raise StateMachineError(f"State machine file does not exist: {path}")
        try:
            with path.open("r", encoding="utf-8") as handle:
                document = yaml.safe_load(handle)
        except Exception as exc:
            raise StateMachineError(f"Unable to parse state machine YAML: {path}") from exc
        if not isinstance(document, dict) or not isinstance(document.get("states"), dict):
            raise StateMachineError("State machine must contain a top-level 'states' mapping")
        return cls(document["states"])

    def _validate_states(self) -> None:
        if not self.states:
            raise StateMachineError("State machine cannot be empty")
        for state, definition in self.states.items():
            if not isinstance(state, str) or not state:
                raise StateMachineError("State names must be non-empty strings")
            if not isinstance(definition, dict):
                raise StateMachineError(f"Definition for {state} must be a mapping")
            next_states = self._next_states_from_definition(state, definition)
            for next_state in next_states:
                if next_state not in self.states:
                    raise StateMachineError(
                        f"State {state} references undefined state {next_state}"
                    )
            if definition.get("final", False) and next_states:
                raise StateMachineError(f"Terminal state {state} cannot have next states")

    @staticmethod
    def _next_states_from_definition(
        state: str, definition: Mapping[str, Any]
    ) -> Set[str]:
        raw_next = definition.get("next", [])
        if isinstance(raw_next, str):
            next_states = {raw_next}
        elif isinstance(raw_next, list):
            if any(not isinstance(item, str) or not item for item in raw_next):
                raise StateMachineError(f"State {state} has invalid next states")
            next_states = set(raw_next)
        else:
            raise StateMachineError(f"State {state} has invalid next definition")
        return next_states

    def next_states(self, state: str | None = None) -> Set[str]:
        state_name = state or self.current_state
        if state_name not in self.states:
            raise StateMachineError(f"Unknown state: {state_name}")
        return self._next_states_from_definition(state_name, self.states[state_name])

    def is_terminal(self, state: str | None = None) -> bool:
        state_name = state or self.current_state
        if state_name not in self.states:
            raise StateMachineError(f"Unknown state: {state_name}")
        return bool(self.states[state_name].get("final", False))

    def can_transition(self, target: str) -> bool:
        return target in self.next_states()

    def transition(self, target: str) -> str:
        if self.is_terminal():
            raise StateMachineError(
                f"Cannot transition out of terminal state {self.current_state}",
                code="STATE_TERMINAL",
            )
        if target == "RECOVERY" and not self.can_recover():
            raise StateMachineError(
                "Recovery attempts are exhausted",
                code="RECOVERY_EXHAUSTED",
            )
        if not self.can_transition(target):
            raise StateMachineError(
                f"Illegal transition: {self.current_state} -> {target}",
                code="ILLEGAL_STATE_TRANSITION",
            )
        if target == "RECOVERY":
            self.recovery_attempts += 1
        self.current_state = target
        return self.current_state

    def can_recover(self) -> bool:
        return self.recovery_attempts < self.max_recovery_attempts
