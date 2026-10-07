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
    screen = engine.rootObjects()[0]
    assert screen is not None

    moving_prompt = screen.findChild(object, "movingPrompt")
    finish_container = screen.findChild(object, "finishContainer")
    assert moving_prompt is not None
    assert finish_container is not None

    # While driving, finishReady is False: moving prompt visible, finish container hidden
    assert bridge.finishReady is False
    assert moving_prompt.property("visible") is True
    assert finish_container.property("visible") is False

    # Simulate stopping at finish zone: finish ready toggles visibility
    bridge.set_finish_ready(True)
    assert bridge.finishReady is True
    assert moving_prompt.property("visible") is False
    assert finish_container.property("visible") is True


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

    assert btn.property("_isDebounced") is False

    # First click emits and activates debounce lock
    btn.triggerClick()
    assert len(clicks) == 1
    assert btn.property("_isDebounced") is True

    # Immediate second click while debounced is blocked
    btn.triggerClick()
    assert len(clicks) == 1

    # After debounce clears, subsequent click emits
    btn.setProperty("_isDebounced", False)
    btn.triggerClick()
    assert len(clicks) == 2


def test_automotive_touch_and_typography_standards(qapp):
    """Verifies that Theme enforces automotive cockpit standards (>=96x72 touch target, >=72px HUD speed)."""
    engine = QQmlApplicationEngine()
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    engine.addImportPath(str(qml_dir))

    theme_file = qml_dir / "Theme.qml"
    engine.load(QUrl.fromLocalFile(str(theme_file)))
    assert len(engine.rootObjects()) > 0
    theme = engine.rootObjects()[0]

    assert theme.property("minTouchTarget") >= 72
    assert theme.property("buttonMinHeight") >= 72
    assert theme.property("buttonMinWidth") >= 96
    assert theme.property("fontDisplay") >= 72
    assert theme.property("fontBody") >= 22



