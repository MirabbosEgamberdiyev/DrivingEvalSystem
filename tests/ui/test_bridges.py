
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
    bridge._allow_mock_fallback = True
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


def test_real_bridge_production_blocks_without_precheck_service(qapp, tmp_path):
    config = SystemConfig.load_from_yaml("config/config.yaml")
    db_file = tmp_path / "test_real_bridge_block.db"
    repo = DatabaseRepository(db_file)
    repo.sync_rules("config/rules.yaml")

    # In production without precheck_service and without mock fallback, precheck MUST block
    bridge = RealBridge(config=config, repository=repo)
    bridge.startPrecheck()
    assert bridge.precheckPassed is False
    assert bridge.currentState == "PRECHECK_BLOCKED"
    assert "Precheck xizmati ulanmagan" in bridge.precheckBlockedReason


def test_real_bridge_with_precheck_service_passed_and_failed(qapp, tmp_path):
    from unittest.mock import MagicMock

    from driving_eval.hardware.precheck import CheckItem, PrecheckReport

    config = SystemConfig.load_from_yaml("config/config.yaml")
    db_file = tmp_path / "test_real_bridge_svc.db"
    repo = DatabaseRepository(db_file)
    repo.sync_rules("config/rules.yaml")

    mock_precheck = MagicMock()
    # Scenario A: Passing precheck
    mock_precheck.run_all_checks.return_value = PrecheckReport(
        passed=True,
        items=[
            CheckItem("CAMERA_FRONT", True, True, "FPS: 30"),
            CheckItem("STORAGE_SPACE", True, True, "Bo'sh joy: 50GB"),
        ],
        block_reasons=[],
    )

    bridge = RealBridge(config=config, repository=repo, precheck_service=mock_precheck)
    bridge.startPrecheck()
    assert bridge.precheckPassed is True
    assert bridge.currentState == "SYSTEM_READY"

    # Scenario B: Failing precheck
    mock_precheck.run_all_checks.return_value = PrecheckReport(
        passed=False,
        items=[
            CheckItem("CAMERA_FRONT", False, True, "Kamera FRONT ishlamayapti"),
        ],
        block_reasons=["Kamera FRONT ishlamayapti"],
    )
    bridge.retryPrecheck()
    assert bridge.precheckPassed is False
    assert bridge.currentState == "PRECHECK_BLOCKED"
    assert "Kamera FRONT ishlamayapti" in bridge.precheckBlockedReason


def test_real_bridge_admin_login_security_and_audit_log(qapp, tmp_path):
    config = SystemConfig.load_from_yaml("config/config.yaml")
    db_file = tmp_path / "test_admin_audit.db"
    repo = DatabaseRepository(db_file)

    bridge = RealBridge(config=config, repository=repo)

    # 1. Incorrect PIN fails and records audit log
    bridge.adminLogin("wrong_pin")
    assert bridge.settingsUnlocked is False

    with repo.get_connection() as conn:
        cur = conn.execute("SELECT action, details FROM admin_audit_log ORDER BY id DESC LIMIT 1;")
        log_row = cur.fetchone()
        assert log_row["action"] == "LOGIN_FAILED"
        assert "Invalid PIN attempt" in log_row["details"]

    # 2. Correct PIN (1234 whose hash is configured) succeeds and records audit log
    bridge.adminLogin("1234")
    assert bridge.settingsUnlocked is True

    with repo.get_connection() as conn:
        cur = conn.execute("SELECT action, details FROM admin_audit_log ORDER BY id DESC LIMIT 1;")
        log_row = cur.fetchone()
        assert log_row["action"] == "LOGIN_SUCCESS"
        assert "Admin PIN authentication succeeded" in log_row["details"]

