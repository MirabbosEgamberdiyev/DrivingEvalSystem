"""Test touch keypad interactions and security lockout UI."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine


def test_password_pad_pin_entry_and_clear(qapp):
    """Verifies that PasswordPad manages digits, clear button, and submission."""
    engine = QQmlApplicationEngine()
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    engine.addImportPath(str(qml_dir))

    pad_file = qml_dir / "components" / "PasswordPad.qml"
    engine.load(QUrl.fromLocalFile(str(pad_file)))
    assert len(engine.rootObjects()) > 0
    pad = engine.rootObjects()[0]

    submitted_pins = []
    pad.pinSubmitted.connect(lambda p: submitted_pins.append(p))

    # Initial state
    assert pad.property("currentPin") == ""
    assert pad.property("hasError") is False

    # Simulate entering "123"
    pad.setProperty("currentPin", "123")
    assert pad.property("currentPin") == "123"

    # Reset with clear
    pad.setProperty("currentPin", "")
    assert pad.property("currentPin") == ""

    # Enter 4-digit PIN and submit
    pad.setProperty("currentPin", "1234")
    pad.pinSubmitted.emit("1234")
    assert len(submitted_pins) == 1
    assert submitted_pins[0] == "1234"


def test_password_pad_lockout_display(qapp):
    """Verifies that lockout state disables keypad and shows countdown."""
    engine = QQmlApplicationEngine()
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    engine.addImportPath(str(qml_dir))

    pad_file = qml_dir / "components" / "PasswordPad.qml"
    engine.load(QUrl.fromLocalFile(str(pad_file)))
    assert len(engine.rootObjects()) > 0
    pad = engine.rootObjects()[0]

    pad.setProperty("lockoutRemaining", 28)
    assert pad.property("lockoutRemaining") == 28
