"""Security test suite: Salted PBKDF2 PIN verification, persistent lockout, and audit trails."""

import hashlib

from driving_eval.core.config_schema import SystemConfig
from driving_eval.db.repository import DatabaseRepository
from driving_eval.ui_qml.bridge.real_bridge import RealBridge


def test_pbkdf2_salted_pin_verification(tmp_path):
    db_file = tmp_path / "test_sec.db"
    repo = DatabaseRepository(db_file)

    cfg = SystemConfig.load_from_yaml("config/config.yaml")

    # Generate PBKDF2 salted hash for test PIN "8520"
    salt = bytes.fromhex("0123456789abcdef0123456789abcdef")
    pin = "8520"
    pbkdf2_hash = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100_000).hex()

    cfg.security.admin_pin_pbkdf2 = pbkdf2_hash
    cfg.security.admin_pin_salt = salt.hex()
    cfg.security.max_failed_attempts = 3
    cfg.security.lockout_duration_seconds = 300

    bridge = RealBridge(config=cfg, repository=repo)

    # 1. Backdoor "1234" must FAIL
    unlocked_events = []
    bridge.settingsUnlockedChanged.connect(lambda v: unlocked_events.append(v))

    bridge.adminLogin("1234")
    assert bridge.get_settings_unlocked() is False
    assert unlocked_events[-1] is False

    # 2. Correct PIN unlocks
    bridge.adminLogin("8520")
    assert bridge.get_settings_unlocked() is True
    assert unlocked_events[-1] is True

    # 3. Audit trail contains both failed and success
    with repo.get_connection() as conn:
        rows = conn.execute("SELECT * FROM admin_audit_log ORDER BY id ASC").fetchall()
        assert len(rows) >= 2
        assert rows[-2]["action"] == "LOGIN_FAILED"
        assert rows[-1]["action"] == "LOGIN_SUCCESS"


def test_persistent_lockout_across_app_restart(tmp_path):
    db_file = tmp_path / "test_lockout.db"
    repo = DatabaseRepository(db_file)
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    cfg.security.max_failed_attempts = 3
    cfg.security.lockout_duration_seconds = 300

    bridge1 = RealBridge(config=cfg, repository=repo)

    lockout_events = []
    bridge1.lockoutRemainingChanged.connect(lambda s: lockout_events.append(s))

    # 3 failed attempts
    bridge1.adminLogin("wrong1")
    bridge1.adminLogin("wrong2")
    bridge1.adminLogin("wrong3")

    # Lockout must trigger for 300 seconds (5 minutes)
    assert bridge1.get_lockout_remaining() >= 298
    assert bridge1.get_lockout_remaining() <= 300
    assert 300 in lockout_events

    # Attempt during lockout is immediately rejected
    bridge1.adminLogin("0000")
    assert bridge1.get_settings_unlocked() is False

    # Simulate Application RESTART / CRASH by instantiating a new RealBridge
    bridge2 = RealBridge(config=cfg, repository=repo)

    # Lockout state must PERSIST from SQLite
    assert bridge2.get_lockout_remaining() >= 295
    assert bridge2.get_lockout_remaining() <= 300

    # Even with correct PIN during lockout, login is blocked
    bridge2.adminLogin("1234")
    assert bridge2.get_settings_unlocked() is False


def test_student_role_cannot_bypass_pin_to_unlock_settings(tmp_path):
    db_file = tmp_path / "test_student.db"
    repo = DatabaseRepository(db_file)
    cfg = SystemConfig.load_from_yaml("config/config.yaml")

    bridge = RealBridge(config=cfg, repository=repo)
    bridge.set_current_role("STUDENT")
    assert bridge.get_current_role() == "STUDENT"

    # Student cannot unlock settings
    assert bridge.get_settings_unlocked() is False

    # Admin logout resets unlock flag
    bridge._settings_unlocked = True
    bridge.adminLogout()
    assert bridge.get_settings_unlocked() is False
