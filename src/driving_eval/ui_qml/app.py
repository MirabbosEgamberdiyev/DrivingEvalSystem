"""QML UI Application entry point for Standalone 4-Camera Driving Training & Evaluation System.

Supports --simulate, --windowed, --kiosk, and resolution options. 100% offline.
"""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.logging_config import setup_logging
from driving_eval.db.repository import DatabaseRepository
from driving_eval.ui_qml.bridge.mock_bridge import MockBridge
from driving_eval.ui_qml.bridge.real_bridge import RealBridge
from driving_eval.ui_qml.i18n import I18nService


def parse_resolution(res_str: str) -> tuple[int, int]:
    """Parses WIDTHxHEIGHT resolution string."""
    try:
        parts = res_str.lower().split("x")
        return int(parts[0]), int(parts[1])
    except Exception:
        return 1280, 800


def run_qml_app(argv: list[str] | None = None) -> int:
    """Initializes and runs the QML UI application."""
    parser = argparse.ArgumentParser(
        description="Standalone 4-Camera Driving Training & Evaluation System (QML UI)"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run with MockBridge simulating hardware, sensors, and candidate lifecycle",
    )
    parser.add_argument(
        "--scenario",
        default="normal_pass",
        choices=["normal_pass", "camera_fail", "double_violation", "critical_fail"],
        help="Mock scenario to run when --simulate is active",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Run in windowed mode rather than fullscreen",
    )
    parser.add_argument(
        "--kiosk",
        action="store_true",
        help="Run in strict fullscreen kiosk mode",
    )
    parser.add_argument(
        "--resolution",
        default="1280x800",
        help="Window resolution in WIDTHxHEIGHT (e.g. 1024x600, 1280x800, 1920x1080)",
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to system configuration YAML file",
    )
    parser.add_argument(
        "--auto-demo",
        action="store_true",
        help="Automatically advance through complete lifecycle demonstration",
    )
    parser.add_argument(
        "--demo-exit",
        action="store_true",
        help="Exit automatically after auto-demo completes (useful for automated testing/CI)",
    )
    parser.add_argument(
        "--lang",
        default="uz-Latn",
        choices=["uz-Latn", "uz-Cyrl", "ru", "uz"],
        help="Active UI language (uz-Latn, uz-Cyrl, ru)",
    )

    args = parser.parse_args(argv)

    app = QGuiApplication(sys.argv)
    app.setApplicationName("DrivingEvaluationSystem")
    app.setOrganizationName("AutoExamAI")

    width, height = parse_resolution(args.resolution)

    # Initialize i18n
    i18n = I18nService(default_lang=args.lang)

    # Initialize Bridge (Mock or Real)
    if args.simulate:
        bridge = MockBridge(scenario=args.scenario)
    else:
        # Load production config & services
        config = SystemConfig.load_from_yaml(args.config)
        setup_logging(config.app.log_file, config.app.log_level)
        repository = DatabaseRepository(config.storage.db_path)
        bridge = RealBridge(config=config, repository=repository)

    # Setup QML Engine
    engine = QQmlApplicationEngine()

    qml_dir = Path(__file__).parent / "qml"
    engine.addImportPath(str(qml_dir.resolve()))
    engine.addImportPath(str(qml_dir.parent.resolve()))

    # Expose bridge and i18n to QML root context
    root_context = engine.rootContext()
    root_context.setContextProperty("backendBridge", bridge)
    root_context.setContextProperty("i18n", i18n)

    main_qml_path = qml_dir / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml_path.resolve())))

    if not engine.rootObjects():
        print("Error: QML engine failed to load Main.qml", file=sys.stderr)
        return 1

    window = engine.rootObjects()[0]
    window.setWidth(width)
    window.setHeight(height)

    if args.kiosk and not args.windowed:
        window.showFullScreen()
    else:
        window.show()

    # If --auto-demo is set, orchestrate full lifecycle demonstration
    if args.auto_demo:
        from PySide6.QtCore import QTimer

        # Step 1: Precheck
        QTimer.singleShot(1000, lambda: bridge.startPrecheck())
        # Step 2: System Ready
        QTimer.singleShot(2500, lambda: bridge.proceedToReady())
        # Step 3: Start active test
        QTimer.singleShot(4000, lambda: bridge.startTest())
        # Step 4: Finish test when stopped
        QTimer.singleShot(15000, lambda: bridge.finishTest())
        # Step 5: View Violations List
        QTimer.singleShot(18000, lambda: bridge.requestViolations())
        # Step 6: Open Evidence
        QTimer.singleShot(21000, lambda: bridge.openEvidence("EVT-0001"))
        # Step 7: Return Home
        QTimer.singleShot(24000, lambda: bridge.resetToHome())

        if args.demo_exit:
            QTimer.singleShot(26000, lambda: sys.exit(0))

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_qml_app())
