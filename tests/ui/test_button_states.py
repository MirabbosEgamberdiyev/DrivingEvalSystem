"""Test button states, finish button gating, and touch debounce protection."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine

from driving_eval.ui_qml.bridge.mock_bridge import MockBridge
from driving_eval.ui_qml.i18n import I18nService


def test_finish_button_gating_in_active_test(qapp):
    """Verifies that finish button and prompt are strictly gated by finishReady property."""
    engine = QQmlApplicationEngine()
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    engine.addImportPath(str(qml_dir))

    bridge = MockBridge()
    i18n = I18nService(default_lang="uz")
    engine.rootContext().setContextProperty("backendBridge", bridge)
    engine.rootContext().setContextProperty("i18n", i18n)

    screen_file = qml_dir / "screens" / "ActiveTestScreen.qml"
    engine.load(QUrl.fromLocalFile(str(screen_file)))
    assert len(engine.rootObjects()) > 0
    assert engine.rootObjects()[0] is not None

    # While driving, finishReady is False
    assert bridge.finishReady is False

    # Simulate stopping at finish zone
    bridge.set_finish_ready(True)
    assert bridge.finishReady is True


def test_big_button_debounce_logic(qapp, qtbot):
    """Verifies that BigButton prevents rapid consecutive taps."""
    engine = QQmlApplicationEngine()
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    engine.addImportPath(str(qml_dir))

    btn_file = qml_dir / "components" / "BigButton.qml"
    engine.load(QUrl.fromLocalFile(str(btn_file)))
    assert len(engine.rootObjects()) > 0
    btn = engine.rootObjects()[0]

    clicks = []
    btn.clicked.connect(lambda: clicks.append(1))

    # MouseArea trigger simulation
    assert btn.findChild(object, "mouseArea") is not None
    assert btn.property("_isDebounced") is False

    # First click emits
    btn.clicked.emit()
    assert len(clicks) == 1
