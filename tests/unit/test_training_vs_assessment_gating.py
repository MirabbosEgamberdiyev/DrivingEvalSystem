"""Unit tests for TRAINING vs ASSESSMENT mode gating and N-camera flexibility."""

import pytest
from PySide6.QtCore import QCoreApplication

from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.state_machine import ExamState
from driving_eval.db.repository import DatabaseRepository
from driving_eval.ui_qml.bridge.mock_bridge import MockBridge
from driving_eval.ui_qml.bridge.real_bridge import RealBridge


@pytest.fixture
def qt_app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_gating.db"
    return DatabaseRepository(db_file)


def test_real_bridge_assessment_mode_halts_on_critical_violation(qt_app, repo):
    """In ASSESSMENT mode, a critical violation must immediately abort the exam and record FAILED."""
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    bridge = RealBridge(
        config=cfg,
        repository=repo,
    )
    bridge._allow_mock_fallback = True
    bridge.startPrecheck()
    assert bridge.precheckPassed is True
    assert bridge.currentState == "SYSTEM_READY"

    # Start in ASSESSMENT mode
    bridge.startTestWithMode("ASSESSMENT")
    assert bridge.examMode == "ASSESSMENT"
    assert bridge.currentState == "TEST_ACTIVE"
    assert bridge.state_machine.current_state == ExamState.TEST_ACTIVE

    # Raise critical violation
    bridge.on_violation_detected(
        code="CRITICAL_COLLISION",
        title="To'qnashuv",
        screen_text="Kritik to'qnashuv",
        penalty=100,
        critical=True,
    )

    # Exam must immediately transition to RESULT_READY
    assert bridge.currentState == "RESULT_READY"
    session = repo.get_session(bridge._current_session_id)
    assert session is not None
    assert session["status"] == "FAILED"
    assert session["mode"] == "ASSESSMENT"


def test_real_bridge_training_mode_continues_on_critical_violation(qt_app, repo):
    """In TRAINING mode, a critical violation announces alert but does NOT abort practice."""
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    bridge = RealBridge(
        config=cfg,
        repository=repo,
    )
    bridge._allow_mock_fallback = True
    bridge.startPrecheck()
    assert bridge.precheckPassed is True
    assert bridge.currentState == "SYSTEM_READY"

    # Start in TRAINING mode
    bridge.startTestWithMode("TRAINING")
    assert bridge.examMode == "TRAINING"
    assert bridge.currentState == "TEST_ACTIVE"
    assert bridge.state_machine.current_state == ExamState.TEST_ACTIVE

    # Raise critical violation
    bridge.on_violation_detected(
        code="CRITICAL_COLLISION",
        title="To'qnashuv",
        screen_text="Kritik to'qnashuv",
        penalty=100,
        critical=True,
    )

    # In training mode, exam stays TEST_ACTIVE!
    assert bridge.currentState == "TEST_ACTIVE"
    assert bridge.state_machine.current_state == ExamState.TEST_ACTIVE
    assert len(bridge._recorded_violations) == 1

    # Candidate practices further and finishes
    results_captured = []
    bridge.resultReady.connect(lambda data: results_captured.append(data))
    bridge.finishTest()

    assert bridge.currentState == "RESULT_READY"
    assert len(results_captured) == 1
    res = results_captured[0]
    assert res["mode"] == "TRAINING"
    assert res["official"] is False

    session = repo.get_session(bridge._current_session_id)
    assert session is not None
    assert session["status"] == "TRAINING_COMPLETED"
    assert session["mode"] == "TRAINING"


def test_mock_bridge_training_vs_assessment_critical_scenarios(qt_app):
    """Verifies MockBridge tick simulation behavior in ASSESSMENT vs TRAINING with critical_fail."""
    # 1. ASSESSMENT mode stops at tick 7
    bridge_assess = MockBridge(scenario="critical_fail")
    bridge_assess._precheck_passed = True
    bridge_assess.startTestWithMode("ASSESSMENT")
    assert bridge_assess.examMode == "ASSESSMENT"

    # Fast forward ticks up to 7
    for _ in range(7):
        bridge_assess._on_test_tick()

    assert bridge_assess.currentState == "RESULT_READY"
    assert bridge_assess._test_timer.isActive() is False

    # 2. TRAINING mode continues through tick 7
    bridge_train = MockBridge(scenario="critical_fail")
    bridge_train._precheck_passed = True
    bridge_train.startTestWithMode("TRAINING")
    assert bridge_train.examMode == "TRAINING"

    for _ in range(7):
        bridge_train._on_test_tick()

    # Still active!
    assert bridge_train.currentState == "TEST_ACTIVE"
    assert bridge_train._critical_count == 1

    # Continue to tick 10 to finish
    for _ in range(3):
        bridge_train._on_test_tick()

    assert bridge_train.finishReady is True
    bridge_train.finishTest()
    assert bridge_train.currentState == "RESULT_READY"
