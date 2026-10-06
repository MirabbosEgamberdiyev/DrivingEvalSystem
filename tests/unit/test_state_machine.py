"""Unit tests for the strict ExamStateMachine."""

import pytest

from driving_eval.core.exceptions import InvalidStateTransitionError
from driving_eval.core.state_machine import ExamState, ExamStateMachine
from driving_eval.db.repository import DatabaseRepository


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "sm_test.db"
    return DatabaseRepository(db_file)


def test_normal_lifecycle_transitions(repo):
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


def test_critical_violation_lifecycle(repo):
    sm = ExamStateMachine(repository=repo, initial_state=ExamState.TEST_READY)
    sm.transition_to(ExamState.TEST_ACTIVE, "Test boshlandi")

    # Critical violation occurs!
    sm.transition_to(ExamState.CRITICAL_VIOLATION, "To'qnashuv aniqlandi")
    assert not sm.is_scoring_active()

    sm.transition_to(ExamState.TERMINATED, "Test to'xtatildi")
    sm.transition_to(ExamState.RESULT_READY, "Kritik natija tayyorlandi")
    sm.transition_to(ExamState.COMPLETED, "Yakunlandi")
    assert sm.current_state == ExamState.COMPLETED


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
    ],
)
def test_illegal_transitions_raise_exception(from_state, to_state):
    sm = ExamStateMachine(initial_state=from_state)
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(to_state)


def test_state_listeners(repo):
    transitions = []

    def on_transition(src, dst, reason):
        transitions.append((src, dst, reason))

    sm = ExamStateMachine(repository=repo)
    sm.subscribe(on_transition)

    sm.transition_to(ExamState.BOOT, "Booting")
    sm.transition_to(ExamState.READY, "System is ready")

    assert len(transitions) == 2
    assert transitions[0] == (ExamState.IDLE, ExamState.BOOT, "Booting")
    assert transitions[1] == (ExamState.BOOT, ExamState.READY, "System is ready")
