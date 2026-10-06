"""Strict finite state machine for driving examination and application lifecycle.

Boolean flags are strictly prohibited for tracking lifecycle states.
All transitions are validated against formal transition tables, and recorded
in SQLite system_logs. Unauthorized transitions raise InvalidStateTransitionError.

Architectural Tiers:
1. ApplicationStateMachine:
   UNLICENSED -> SETUP_REQUIRED -> READY
2. ExamStateMachine:
   IDLE -> BOOT -> READY -> PRECHECK -> CAMERA_CHECK -> SYSTEM_CHECK ->
   TEST_READY -> TEST_ACTIVE -> FINISH_DETECTED -> VEHICLE_STOPPED ->
   FINALIZING -> RESULT_READY -> COMPLETED
   Critical flow: TEST_ACTIVE -> CRITICAL_VIOLATION -> TERMINATED -> RESULT_READY
   Power-loss flow: TEST_ACTIVE -> INTERRUPTED -> READY
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum

from driving_eval.core.exceptions import InvalidStateTransitionError
from driving_eval.db.repository import DatabaseRepository

logger = logging.getLogger("driving_eval.state_machine")


# =====================================================================
# 1. APPLICATION STATE MACHINE (Tier 1)
# =====================================================================


class ApplicationState(str, Enum):
    """System-level readiness and licensing lifecycle state."""

    UNLICENSED = "UNLICENSED"          # License key not provided or invalid
    SETUP_REQUIRED = "SETUP_REQUIRED"  # License valid, but hardware/polygon setup incomplete
    READY = "READY"                    # Fully licensed, configured, ready for exams


APPLICATION_ALLOWED_TRANSITIONS: dict[ApplicationState, set[ApplicationState]] = {
    ApplicationState.UNLICENSED: {
        ApplicationState.SETUP_REQUIRED,
        ApplicationState.READY,
    },
    ApplicationState.SETUP_REQUIRED: {
        ApplicationState.READY,
        ApplicationState.UNLICENSED,
    },
    ApplicationState.READY: {
        ApplicationState.SETUP_REQUIRED,
        ApplicationState.UNLICENSED,
    },
}


class ApplicationStateMachine:
    """Manages high-level system lifecycle: licensing, initial calibration wizard, readiness."""

    def __init__(
        self,
        repository: DatabaseRepository | None = None,
        initial_state: ApplicationState = ApplicationState.UNLICENSED,
    ) -> None:
        self._state: ApplicationState = initial_state
        self._repository = repository
        self._listeners: list[Callable[[ApplicationState, ApplicationState, str], None]] = []

    @property
    def current_state(self) -> ApplicationState:
        return self._state

    def is_ready(self) -> bool:
        """Returns True if the system is fully licensed and configured for testing."""
        return self._state == ApplicationState.READY

    def subscribe(self, callback: Callable[[ApplicationState, ApplicationState, str], None]) -> None:
        """Subscribes a listener to transition events: callback(from_state, to_state, reason)."""
        self._listeners.append(callback)

    def can_transition(self, target_state: ApplicationState) -> bool:
        """Checks if a transition to target_state is permitted from current state."""
        allowed = APPLICATION_ALLOWED_TRANSITIONS.get(self._state, set())
        return target_state in allowed

    def transition_to(self, target_state: ApplicationState, reason: str = "") -> None:
        """Executes an application-level state transition."""
        if not self.can_transition(target_state):
            err_msg = (
                f"Noqonuniy application o'tishi: '{self._state.value}' -> '{target_state.value}'. "
                f"Ruxsat etilganlar: {[s.value for s in APPLICATION_ALLOWED_TRANSITIONS.get(self._state, set())]}"
            )
            logger.error(err_msg)
            if self._repository:
                self._repository.log_system_event(
                    level="ERROR",
                    module="application_state_machine",
                    message=err_msg,
                    state=self._state.value,
                )
            raise InvalidStateTransitionError(self._state.value, target_state.value, reason)

        prev_state = self._state
        self._state = target_state

        log_message = (
            f"Application state o'zgardi: {prev_state.value} -> {target_state.value} "
            f"(Sabab: {reason or 'Oddiy oqim'})"
        )
        logger.info(log_message)

        if self._repository:
            self._repository.log_system_event(
                level="INFO",
                module="application_state_machine",
                message=log_message,
                state=target_state.value,
            )

        for listener in self._listeners:
            try:
                listener(prev_state, target_state, reason)
            except Exception as e:
                logger.error("Application state listener xatosi (%s): %s", listener, e)


# =====================================================================
# 2. EXAM STATE MACHINE (Tier 2)
# =====================================================================


class ExamState(str, Enum):
    """Exam-level candidate testing lifecycle state."""

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
    ExamState.BOOT: {ExamState.READY, ExamState.IDLE},
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
        app_state_machine: ApplicationStateMachine | None = None,
    ) -> None:
        self._state: ExamState = initial_state
        self._repository = repository
        self._app_state_machine = app_state_machine
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
        if target_state not in allowed:
            return False

        # If coupled with ApplicationStateMachine, gate active testing on Application readiness
        if target_state in (ExamState.PRECHECK, ExamState.TEST_ACTIVE) and self._app_state_machine:
            if not self._app_state_machine.is_ready():
                return False

        return True

    def transition_to(self, target_state: ExamState, reason: str = "") -> None:
        """Executes a transition.

        Raises InvalidStateTransitionError if the transition is prohibited.
        """
        if not self.can_transition(target_state):
            # Provide exact explanatory reason if blocked by ApplicationStateMachine
            if (
                target_state in (ExamState.PRECHECK, ExamState.TEST_ACTIVE)
                and self._app_state_machine
                and not self._app_state_machine.is_ready()
            ):
                err_msg = (
                    f"Test boshlanishi bloklandi: Application state '{self._app_state_machine.current_state.value}' "
                    f"READY emas (Litsenziya yoki sozlash talab qilinadi)."
                )
            else:
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
            detail = f"{reason} ({err_msg})" if reason else err_msg
            raise InvalidStateTransitionError(self._state.value, target_state.value, detail)

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
