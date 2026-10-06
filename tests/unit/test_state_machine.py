"""Unit tests for the strict 2-tier Application and Exam State Machines."""

from __future__ import annotations

from pathlib import Path

import pytest

from driving_eval.core.exceptions import InvalidStateTransitionError
from driving_eval.core.state_machine import (
    ApplicationState,
    ApplicationStateMachine,
    ExamState,
    ExamStateMachine,
)
from driving_eval.db.repository import DatabaseRepository
from driving_eval.maintenance.session_recovery import SessionRecoveryService


@pytest.fixture
def repo(tmp_path: Path) -> DatabaseRepository:
    db_file = tmp_path / "sm_test.db"
    return DatabaseRepository(db_file)


# =====================================================================
# Application State Machine Tests
# =====================================================================


def test_application_state_machine_valid_transitions(repo: DatabaseRepository) -> None:
    app_sm = ApplicationStateMachine(repository=repo, initial_state=ApplicationState.UNLICENSED)
    assert app_sm.current_state == ApplicationState.UNLICENSED
    assert not app_sm.is_ready()

    # UNLICENSED -> SETUP_REQUIRED
    app_sm.transition_to(ApplicationState.SETUP_REQUIRED, "Valid license entered")
    assert app_sm.current_state == ApplicationState.SETUP_REQUIRED
    assert not app_sm.is_ready()

    # SETUP_REQUIRED -> READY
    app_sm.transition_to(ApplicationState.READY, "Calibration wizard completed")
    assert app_sm.current_state == ApplicationState.READY
    assert app_sm.is_ready()

    # READY -> SETUP_REQUIRED (recalibration)
    app_sm.transition_to(ApplicationState.SETUP_REQUIRED, "Camera position adjusted")
    assert not app_sm.is_ready()

    # SETUP_REQUIRED -> UNLICENSED (license revoked)
    app_sm.transition_to(ApplicationState.UNLICENSED, "License reset")
    assert app_sm.current_state == ApplicationState.UNLICENSED


def test_application_state_machine_direct_unlicensed_to_ready(repo: DatabaseRepository) -> None:
    app_sm = ApplicationStateMachine(repository=repo, initial_state=ApplicationState.UNLICENSED)
    app_sm.transition_to(ApplicationState.READY, "Pre-calibrated machine activated")
    assert app_sm.is_ready()


def test_application_state_machine_listeners(repo: DatabaseRepository) -> None:
    events = []
    app_sm = ApplicationStateMachine(repository=repo, initial_state=ApplicationState.UNLICENSED)
    app_sm.subscribe(lambda src, dst, r: events.append((src, dst, r)))

    app_sm.transition_to(ApplicationState.SETUP_REQUIRED, "Activated")
    assert len(events) == 1
    assert events[0] == (ApplicationState.UNLICENSED, ApplicationState.SETUP_REQUIRED, "Activated")


# =====================================================================
# Exam State Machine Tests
# =====================================================================


def test_normal_lifecycle_transitions(repo: DatabaseRepository) -> None:
    sm = ExamStateMachine(repository=repo)
    assert sm.current_state == ExamState.IDLE
    assert not sm.is_scoring_active()

    # Step by step through full normal lifecycle
    sm.transition_to(ExamState.BOOT, "Tizim yoqilmoqda")
    sm.transition_to(ExamState.READY, "Tayyor holat")
    sm.transition_to(ExamState.PRECHECK, "Precheck boshlandi")
    sm.transition_to(ExamState.CAMERA_CHECK, "Kameralar tekshiruvi")
    sm.transition_to(ExamState.SYSTEM_CHECK, "Tizim komponentlari")
    sm.transition_to(ExamState.TEST_READY, "Barcha tekshiruvlar yashil")
    assert not sm.is_scoring_active()

    sm.transition_to(ExamState.TEST_ACTIVE, "Test start bosildi")
    assert sm.is_scoring_active()

    sm.transition_to(ExamState.FINISH_DETECTED, "Finish chizig'i ko'rindi")
    assert sm.is_scoring_active()

    sm.transition_to(ExamState.VEHICLE_STOPPED, "Mashina tezligi 0")
    assert not sm.is_scoring_active()

    sm.transition_to(ExamState.FINALIZING, "Dalillar yopilmoqda")
    sm.transition_to(ExamState.RESULT_READY, "Natija hisoblandi")
    sm.transition_to(ExamState.COMPLETED, "Imtihon yakunlandi")
    assert sm.current_state == ExamState.COMPLETED

    # Next candidate transition
    sm.transition_to(ExamState.READY, "Keyingi nomzod")
    assert sm.current_state == ExamState.READY


def test_critical_violation_lifecycle(repo: DatabaseRepository) -> None:
    sm = ExamStateMachine(repository=repo, initial_state=ExamState.TEST_READY)
    sm.transition_to(ExamState.TEST_ACTIVE, "Test boshlandi")

    # Critical violation occurs!
    sm.transition_to(ExamState.CRITICAL_VIOLATION, "To'qnashuv aniqlandi")
    assert not sm.is_scoring_active()

    sm.transition_to(ExamState.TERMINATED, "Test to'xtatildi")
    sm.transition_to(ExamState.RESULT_READY, "Kritik natija tayyorlandi")
    sm.transition_to(ExamState.COMPLETED, "Yakunlandi")
    assert sm.current_state == ExamState.COMPLETED


def test_interrupted_power_loss_lifecycle(repo: DatabaseRepository) -> None:
    sm = ExamStateMachine(repository=repo, initial_state=ExamState.TEST_ACTIVE)
    assert sm.is_scoring_active()

    # Power loss or interruption
    sm.transition_to(ExamState.INTERRUPTED, "Quvvat uzilishi yuz berdi")
    assert not sm.is_scoring_active()

    sm.transition_to(ExamState.READY, "Qayta tiklandi, yangi testga tayyor")
    assert sm.current_state == ExamState.READY


# =====================================================================
# Gating: Coupling Application SM with Exam SM
# =====================================================================


def test_exam_start_blocked_when_application_not_ready(repo: DatabaseRepository) -> None:
    """Verifies that ExamStateMachine cannot enter PRECHECK if Application is UNLICENSED or SETUP_REQUIRED."""
    app_sm = ApplicationStateMachine(repository=repo, initial_state=ApplicationState.UNLICENSED)
    exam_sm = ExamStateMachine(
        repository=repo,
        initial_state=ExamState.READY,
        app_state_machine=app_sm,
    )

    # 1. Blocked when UNLICENSED
    assert not exam_sm.can_transition(ExamState.PRECHECK)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        exam_sm.transition_to(ExamState.PRECHECK, "Test boshlashga urinish")
    assert "UNLICENSED" in str(exc_info.value)

    # 2. Blocked when SETUP_REQUIRED
    app_sm.transition_to(ApplicationState.SETUP_REQUIRED, "Licensed")
    assert not exam_sm.can_transition(ExamState.PRECHECK)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        exam_sm.transition_to(ExamState.PRECHECK, "Test boshlashga urinish")
    assert "SETUP_REQUIRED" in str(exc_info.value)

    # 3. Allowed once Application is READY
    app_sm.transition_to(ApplicationState.READY, "Setup completed")
    assert exam_sm.can_transition(ExamState.PRECHECK)
    exam_sm.transition_to(ExamState.PRECHECK, "Precheck muvaffaqiyatli boshlandi")
    assert exam_sm.current_state == ExamState.PRECHECK


# =====================================================================
# Illegal Transitions and Audit Logging
# =====================================================================


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (ExamState.IDLE, ExamState.TEST_ACTIVE),
        (ExamState.READY, ExamState.COMPLETED),
        (ExamState.PRECHECK, ExamState.TEST_ACTIVE),
        (ExamState.TEST_READY, ExamState.COMPLETED),
        (ExamState.COMPLETED, ExamState.TEST_ACTIVE),
        (ExamState.CRITICAL_VIOLATION, ExamState.TEST_ACTIVE),
        (ExamState.TERMINATED, ExamState.TEST_ACTIVE),
        (ExamState.VEHICLE_STOPPED, ExamState.TEST_ACTIVE),
    ],
)
def test_illegal_transitions_raise_exception(from_state: ExamState, to_state: ExamState) -> None:
    sm = ExamStateMachine(initial_state=from_state)
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(to_state)


def test_state_listeners(repo: DatabaseRepository) -> None:
    transitions = []

    def on_transition(src: ExamState, dst: ExamState, reason: str) -> None:
        transitions.append((src, dst, reason))

    sm = ExamStateMachine(repository=repo)
    sm.subscribe(on_transition)

    sm.transition_to(ExamState.BOOT, "Booting")
    sm.transition_to(ExamState.READY, "System is ready")

    assert len(transitions) == 2
    assert transitions[0] == (ExamState.IDLE, ExamState.BOOT, "Booting")
    assert transitions[1] == (ExamState.BOOT, ExamState.READY, "System is ready")


def test_state_machine_records_logs_in_database(repo: DatabaseRepository) -> None:
    """Verifies that all transitions are logged into SQLite system_logs table."""
    sm = ExamStateMachine(repository=repo)
    sm.set_session_id("SESS-AUDIT-TEST")

    sm.transition_to(ExamState.BOOT, "Power on boot")
    sm.transition_to(ExamState.READY, "Self-tests ok")

    # Read back system_logs from DB
    with repo.get_connection() as conn:
        cursor = conn.execute("SELECT * FROM system_logs WHERE session_id = 'SESS-AUDIT-TEST' ORDER BY id ASC")
        rows = cursor.fetchall()

    assert len(rows) == 2
    assert "IDLE -> BOOT" in rows[0]["message"]
    assert "BOOT -> READY" in rows[1]["message"]
    assert rows[0]["module"] == "state_machine"


def test_session_recovery_manager_integration(repo: DatabaseRepository) -> None:
    """Simulates power outage during TEST_ACTIVE and verifies recovery on reboot."""
    student_id = repo.register_or_get_student("PASS-RECOV", "Rustam", "Karimov")
    vehicle_id = repo.register_vehicle("CAR-RECOV", "VIN-RECOV", "01B999BB", "Nexia", 2023)

    session_id = "SESS-POWER-OUTAGE"
    repo.create_session(
        session_id=session_id,
        student_id=student_id,
        vehicle_id=vehicle_id,
        start_score=100,
        rules_version="2026.1",
        app_version="1.0.0",
        mode="ASSESSMENT",
    )

    # Machine reboots: recovery service detects unfinished session
    recovery_svc = SessionRecoveryService(repository=repo, mode="SAFE_INTERRUPT")
    recovered = recovery_svc.check_and_recover_on_boot()

    assert len(recovered) == 1
    assert recovered[0]["id"] == session_id

    # Verify session is marked INTERRUPTED in database
    closed_sess = repo.get_session(session_id)
    assert closed_sess is not None
    assert closed_sess["status"] == "INTERRUPTED"
    assert closed_sess["result"] == "INCOMPLETE"
