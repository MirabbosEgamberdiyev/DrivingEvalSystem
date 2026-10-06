
from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.state_machine import ExamState
from driving_eval.db.repository import DatabaseRepository
from driving_eval.ui_qml.bridge.mock_bridge import MockBridge
from driving_eval.ui_qml.bridge.real_bridge import RealBridge


def test_mock_bridge_initial_state(qapp):
    bridge = MockBridge()
    assert bridge.currentState == "HOME"
    assert bridge.finishReady is False
    assert bridge.isConnected is True
    assert bridge.carId == "CAR-01"
    assert bridge.settingsUnlocked is False
    assert bridge.lockoutRemaining == 0


def test_mock_bridge_precheck_normal(qapp, qtbot):
    bridge = MockBridge(scenario="normal_pass")

    with qtbot.waitSignal(bridge.stateChanged, timeout=1500) as blocker:
        bridge.startPrecheck()

    # Precheck should finish and transition to SYSTEM_READY
    assert blocker.args == ["PRECHECK"]

    # Wait for completion timer
    qtbot.wait(600)
    assert bridge.precheckPassed is True
    assert bridge.currentState == "SYSTEM_READY"
    assert bridge.precheckBlockedReason == ""


def test_mock_bridge_precheck_failure_and_retry(qapp, qtbot):
    bridge = MockBridge(scenario="camera_fail")
    bridge.startPrecheck()

    qtbot.wait(600)
    assert bridge.precheckPassed is False
    assert bridge.currentState == "PRECHECK_BLOCKED"
    assert "Orqa kamera" in bridge.precheckBlockedReason

    # Retry should recover
    bridge.retryPrecheck()
    qtbot.wait(600)
    assert bridge.precheckPassed is True
    assert bridge.currentState == "SYSTEM_READY"


def test_mock_bridge_active_test_and_finish_gating(qapp, qtbot):
    bridge = MockBridge(scenario="normal_pass")
    bridge.startTest()
    assert bridge.currentState == "TEST_ACTIVE"
    assert bridge.finishReady is False

    # Attempting to finish before vehicle stops should be ignored
    bridge.finishTest()
    assert bridge.currentState == "TEST_ACTIVE"

    # Simulate reaching finish and stopping
    bridge.set_finish_ready(True)
    assert bridge.finishReady is True

    # Now finishing should transition to RESULT_READY
    with qtbot.waitSignal(bridge.resultReady, timeout=1000) as blocker:
        bridge.finishTest()

    assert bridge.currentState == "RESULT_READY"
    res = blocker.args[0]
    assert res["passed"] is True
    assert res["final_score"] >= 70
    assert "hash" in res


def test_mock_bridge_critical_failure(qapp, qtbot):
    bridge = MockBridge(scenario="critical_fail")
    bridge.startTest()

    # Step simulation to critical violation timestamp (tick 7)
    for _ in range(7):
        bridge._on_test_tick()

    assert bridge._critical_count > 0
    assert bridge.currentState == "RESULT_READY"


def test_mock_bridge_pin_lockout(qapp, qtbot):
    bridge = MockBridge()
    assert bridge.settingsUnlocked is False

    # 1st incorrect PIN
    bridge.adminLogin("0000")
    assert bridge.settingsUnlocked is False
    assert bridge.lockoutRemaining == 0

    # 2nd incorrect PIN
    bridge.adminLogin("1111")
    assert bridge.settingsUnlocked is False
    assert bridge.lockoutRemaining == 0

    # 3rd incorrect PIN triggers 30s lockout
    bridge.adminLogin("2222")
    assert bridge.settingsUnlocked is False
    assert bridge.lockoutRemaining == 30

    # During lockout, correct PIN is rejected
    bridge.adminLogin("1234")
    assert bridge.settingsUnlocked is False

    # Expire lockout
    bridge._lockout_seconds = 0
    bridge._lockout_remaining = 0
    bridge.adminLogin("1234")
    assert bridge.settingsUnlocked is True


def test_mock_bridge_disconnect_recovery(qapp, qtbot):
    bridge = MockBridge()
    assert bridge.isConnected is True

    with qtbot.waitSignal(bridge.connectionStatusChanged, timeout=1000) as blocker:
        bridge.simulate_disconnect(duration_ms=100)

    assert blocker.args == [False]
    assert bridge.isConnected is False

    # Recovery
    qtbot.wait(200)
    assert bridge.isConnected is True


def test_real_bridge_basic_lifecycle(qapp, tmp_path):
    config = SystemConfig.load_from_yaml("config/config.yaml")
    db_file = tmp_path / "test_real_bridge.db"
    repo = DatabaseRepository(db_file)
    repo.sync_rules("config/rules.yaml")

    bridge = RealBridge(config=config, repository=repo)
    assert bridge.currentState == "HOME"
    assert bridge.isConnected is True

    bridge.startPrecheck()
    assert bridge.precheckPassed is True
    assert bridge.currentState == "SYSTEM_READY"

    bridge.startTest()
    assert bridge.currentState == "TEST_ACTIVE"
    assert bridge.state_machine.current_state == ExamState.TEST_ACTIVE

    bridge.adminLogin("1234")
    assert bridge.settingsUnlocked is True

    bridge.resetToHome()
    assert bridge.currentState == "HOME"
