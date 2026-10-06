"""Renders offscreen screenshots for all screens across the 3 target resolutions.

Resolutions tested:
- 1024x600 (Compact 7-10" cockpit touchscreen)
- 1280x800 (Standard 10-12" primary in-cabin display)
- 1920x1080 (Full HD 15" high resolution display)
"""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickView

from driving_eval.ui_qml.bridge.mock_bridge import MockBridge
from driving_eval.ui_qml.i18n import I18nService

RESOLUTIONS = [
    (1024, 600, "1024x600"),
    (1280, 800, "1280x800"),
    (1920, 1080, "1920x1080"),
]


def test_generate_all_screen_screenshots(qapp, qtbot):
    """Renders offscreen screenshots for each screen at each required resolution."""
    output_dir = Path("screenshots")
    output_dir.mkdir(parents=True, exist_ok=True)

    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    bridge = MockBridge()
    i18n = I18nService(default_lang="uz")

    # Sample result data for populated screens
    sample_result = {
        "car_id": "CAR-01",
        "start_score": 100,
        "total_penalty": 10,
        "final_score": 90,
        "mistake_count": 1,
        "critical_count": 0,
        "passed": True,
        "duration_str": "05:20",
        "hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
        "violations": [
            {
                "id": "EVT-0001",
                "code": "CONE_TOUCH",
                "title": "Konusga tegish",
                "screen_text": "Konusga tegish holati aniqlandi",
                "penalty": 10,
                "critical": False,
                "suspect": False,
                "exercise": "ZMEIKA",
                "timestamp": "02:05",
            },
            {
                "id": "EVT-SUSP-01",
                "code": "PEDESTRIAN_SUSPECT",
                "title": "Piyodalar yo'lagi (Shubhali)",
                "screen_text": "Ishonchlilik 78% (<85% chegara) - jarima olinmadi",
                "penalty": 0,
                "critical": False,
                "suspect": True,
                "exercise": "ZMEIKA",
                "timestamp": "02:15",
            },
        ],
    }
    bridge._recorded_violations = sample_result["violations"]
    bridge.resultReady.emit(sample_result)

    screens_to_capture = [
        ("01_home", "screens/HomeScreen.qml"),
        ("02_precheck", "screens/PrecheckScreen.qml"),
        ("03_system_ready", "screens/SystemReadyScreen.qml"),
        ("04_active_test", "screens/ActiveTestScreen.qml"),
        ("05_result", "screens/ResultScreen.qml"),
        ("06_violations_list", "screens/ViolationsListScreen.qml"),
        ("07_evidence", "screens/EvidenceScreen.qml"),
        ("08_settings", "screens/SettingsScreen.qml"),
    ]

    for screen_name, screen_rel in screens_to_capture:
        screen_path = qml_dir / screen_rel
        for w, h, res_label in RESOLUTIONS:
            view = QQuickView()
            view.engine().addImportPath(str(qml_dir))
            view.engine().addImportPath(str(qml_dir.parent))
            view.rootContext().setContextProperty("backendBridge", bridge)
            view.rootContext().setContextProperty("i18n", i18n)

            if "PrecheckScreen" in screen_rel:
                bridge._init_precheck_items()
                bridge.precheckUpdated.emit(bridge._precheck_items)
            elif "ResultScreen" in screen_rel:
                bridge._precheck_passed = True
                bridge.resultReady.emit(sample_result)
            elif "SettingsScreen" in screen_rel:
                bridge.adminLogin("1234")

            view.setResizeMode(QQuickView.SizeRootObjectToView)
            view.resize(w, h)
            view.setSource(QUrl.fromLocalFile(str(screen_path)))
            view.show()
            qtbot.wait(80)

            screen = view.screen() or qapp.primaryScreen()
            pix = screen.grabWindow(view.winId())
            save_path = output_dir / f"{screen_name}_{res_label}.png"
            pix.save(str(save_path))
            assert save_path.exists(), f"Failed to save screenshot: {save_path}"
            assert save_path.stat().st_size > 0
            view.close()

    # Also capture Violation Popup on top of Main.qml
    for w, h, res_label in RESOLUTIONS:
        main_engine = QQmlApplicationEngine()
        main_engine.addImportPath(str(qml_dir))
        main_engine.addImportPath(str(qml_dir.parent))
        main_engine.rootContext().setContextProperty("backendBridge", bridge)
        main_engine.rootContext().setContextProperty("i18n", i18n)

        main_qml = qml_dir / "Main.qml"
        main_engine.load(QUrl.fromLocalFile(str(main_qml)))
        win = main_engine.rootObjects()[0]
        win.setWidth(w)
        win.setHeight(h)
        win.show()

        bridge.startTest()
        bridge.on_violation_detected(
            code="CONE_TOUCH",
            title="Konusga tegish",
            screen_text="Konusga tegish holati aniqlandi",
            penalty=10,
            critical=False,
        )
        qtbot.wait(100)

        screen = win.screen() or qapp.primaryScreen()
        pix = screen.grabWindow(win.winId())
        popup_path = output_dir / f"05_violation_popup_{res_label}.png"
        pix.save(str(popup_path))
        assert popup_path.exists()
        assert popup_path.stat().st_size > 0
        win.close()
