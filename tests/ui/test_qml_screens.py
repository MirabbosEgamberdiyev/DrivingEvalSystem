"""Test loading and compiling of QML screens and Main.qml."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine

from driving_eval.ui_qml.bridge.mock_bridge import MockBridge
from driving_eval.ui_qml.i18n import I18nService


def test_qml_main_and_screens_load(qapp):
    """Verifies that QQmlApplicationEngine can load Main.qml and find all components."""
    engine = QQmlApplicationEngine()
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    engine.addImportPath(str(qml_dir))
    engine.addImportPath(str(qml_dir.parent))

    bridge = MockBridge()
    i18n = I18nService(default_lang="uz")

    engine.rootContext().setContextProperty("backendBridge", bridge)
    engine.rootContext().setContextProperty("i18n", i18n)

    main_qml = qml_dir / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    assert len(engine.rootObjects()) > 0, "Failed to load Main.qml"
    window = engine.rootObjects()[0]
    assert window.property("title") is not None


def test_individual_screens_compile(qapp):
    """Verifies that each screen .qml file can be loaded directly by QQmlApplicationEngine."""
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    screens = [
        "screens/HomeScreen.qml",
        "screens/PrecheckScreen.qml",
        "screens/SystemReadyScreen.qml",
        "screens/ActiveTestScreen.qml",
        "screens/ResultScreen.qml",
        "screens/ViolationsListScreen.qml",
        "screens/EvidenceScreen.qml",
        "screens/SettingsScreen.qml",
        "components/PasswordPad.qml",
        "components/VirtualKeyboard.qml",
    ]

    bridge = MockBridge()
    i18n = I18nService(default_lang="uz")

    for screen_rel in screens:
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        engine.addImportPath(str(qml_dir.parent))
        engine.rootContext().setContextProperty("backendBridge", bridge)
        engine.rootContext().setContextProperty("i18n", i18n)

        screen_file = qml_dir / screen_rel
        assert screen_file.exists(), f"Screen file does not exist: {screen_file}"

        engine.load(QUrl.fromLocalFile(str(screen_file)))
        assert len(engine.rootObjects()) > 0, f"Screen {screen_rel} failed to instantiate"
