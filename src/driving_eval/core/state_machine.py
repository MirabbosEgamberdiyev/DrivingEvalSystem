"""Strict finite state machine for driving examination lifecycle.

Boolean flags are strictly prohibited for tracking lifecycle states.
All transitions are validated against a formal transition table, and recorded
in SQLite system_logs. Unauthorized transitions raise InvalidStateTransitionError.
"""

import logging
from collections.abc import Callable
from enum import Enum

from driving_eval.core.exceptions import InvalidStateTransitionError
from driving_eval.db.repository import DatabaseRepository

logger = logging.getLogger("driving_eval.state_machine")


class ExamState(str, Enum):
    IDLE = "IDLE"
    BOOT = "BOOT"
    READY = "READY"
    PRECHECK = "PRECHECK"
    CAMERA_CHECK = "CAMERA_CHECK"
    SYSTEM_CHECK = "SYSTEM_CHECK"
    TEST_READY = "TEST_READY"
    TEST_ACTIVE = "TEST_ACTIVE"
    FINISH_DETECTED = "FINISH_DETECTED"
    VEHICLE_STOPPED = "VEHICLE_STOPPED"
    FINALIZING = "FINALIZING"
    RESULT_READY = "RESULT_READY"
    COMPLETED = "COMPLETED"
    CRITICAL_VIOLATION = "CRITICAL_VIOLATION"
    TERMINATED = "TERMINATED"
    INTERRUPTED = "INTERRUPTED"


# Formal Transition Matrix: {current_state: set(allowed_target_states)}
ALLOWED_TRANSITIONS: dict[ExamState, set[ExamState]] = {
    ExamState.IDLE: {ExamState.BOOT},
    ExamState.BOOT: {ExamState.READY},
    ExamState.READY: {ExamState.PRECHECK},
    ExamState.PRECHECK: {ExamState.CAMERA_CHECK, ExamState.READY},
    ExamState.CAMERA_CHECK: {ExamState.SYSTEM_CHECK, ExamState.PRECHECK, ExamState.READY},
    ExamState.SYSTEM_CHECK: {ExamState.TEST_READY, ExamState.PRECHECK, ExamState.READY},
    ExamState.TEST_READY: {ExamState.TEST_ACTIVE, ExamState.READY},
    ExamState.TEST_ACTIVE: {
        ExamState.FINISH_DETECTED,
        ExamState.CRITICAL_VIOLATION,
        ExamState.INTERRUPTED,
    },
    ExamState.FINISH_DETECTED: {
        ExamState.VEHICLE_STOPPED,
        ExamState.CRITICAL_VIOLATION,
        ExamState.INTERRUPTED,
    },
    ExamState.VEHICLE_STOPPED: {
        ExamState.FINALIZING,
        ExamState.INTERRUPTED,
    },
    ExamState.FINALIZING: {
        ExamState.RESULT_READY,
        ExamState.INTERRUPTED,
    },
    ExamState.RESULT_READY: {
        ExamState.COMPLETED,
    },
    ExamState.COMPLETED: {
        ExamState.READY,  # Ready for next candidate
    },
    ExamState.CRITICAL_VIOLATION: {
        ExamState.TERMINATED,
    },
    ExamState.TERMINATED: {
        ExamState.RESULT_READY,
    },
    ExamState.INTERRUPTED: {
        ExamState.READY,
    },
}


class ExamStateMachine:
    """Manages state transitions with validation, listener callbacks, and persistence logging."""

    def __init__(
        self,
        repository: DatabaseRepository | None = None,
        initial_state: ExamState = ExamState.IDLE,
    ):
        self._state: ExamState = initial_state
        self._repository = repository
        self._listeners: list[Callable[[ExamState, ExamState, str], None]] = []
        self._current_session_id: str | None = None

    @property
    def current_state(self) -> ExamState:
        return self._state

    def set_session_id(self, session_id: str | None) -> None:
        self._current_session_id = session_id

    def subscribe(self, callback: Callable[[ExamState, ExamState, str], None]) -> None:
        """Subscribes a listener to transition events: callback(from_state, to_state, reason)."""
        self._listeners.append(callback)

    def can_transition(self, target_state: ExamState) -> bool:
        """Checks if a transition to target_state is permitted from current state."""
        allowed = ALLOWED_TRANSITIONS.get(self._state, set())
        return target_state in allowed

    def transition_to(self, target_state: ExamState, reason: str = "") -> None:
        """Executes a transition.

        Raises InvalidStateTransitionError if the transition is prohibited.
        """
        if not self.can_transition(target_state):
            err_msg = (
                f"Noqonuniy o'tish: '{self._state.value}' -> '{target_state.value}'. "
                f"Ruxsat etilganlar: {[s.value for s in ALLOWED_TRANSITIONS.get(self._state, set())]}"
            )
            logger.error(err_msg)
            if self._repository:
                self._repository.log_system_event(
                    level="ERROR",
                    module="state_machine",
                    message=err_msg,
                    session_id=self._current_session_id,
                    state=self._state.value,
                )
            raise InvalidStateTransitionError(self._state.value, target_state.value, reason)

        prev_state = self._state
        self._state = target_state

        log_message = f"State o'zgardi: {prev_state.value} -> {target_state.value} (Sabab: {reason or 'Oddiy oqim'})"
        logger.info(log_message)

        if self._repository:
            self._repository.log_system_event(
                level="INFO",
                module="state_machine",
                message=log_message,
                session_id=self._current_session_id,
                state=target_state.value,
            )

        for listener in self._listeners:
            try:
                listener(prev_state, target_state, reason)
            except Exception as e:
                logger.error("State listener xatosi (%s): %s", listener, e)

    def is_scoring_active(self) -> bool:
        """Returns True ONLY when test is in active state."""
        return self._state in (ExamState.TEST_ACTIVE, ExamState.FINISH_DETECTED)
