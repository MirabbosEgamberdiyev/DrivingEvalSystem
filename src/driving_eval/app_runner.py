"""Application Runner Entrypoint for Standalone Driving Evaluation System.

Supports --simulate, --kiosk, --check modes. 100% offline runtime.
"""

import argparse
import sys

from PySide6.QtWidgets import QApplication

from driving_eval.ai.mock_detector import MockDetector
from driving_eval.audio.audio_service import AudioService
from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.logging_config import setup_logging
from driving_eval.db.repository import DatabaseRepository
from driving_eval.evidence.recorder import EvidenceRecorder
from driving_eval.evidence.storage import StorageManager
from driving_eval.hardware.camera_service import MultiCameraService
from driving_eval.maintenance.session_recovery import SessionRecoveryService
from driving_eval.ui.app import DrivingEvaluationApp


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Standalone 4-Camera Offline AI Driving Training & Evaluation System"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Mashina va kameralarsiz sintetik video va telemetriya bilan to'liq simulyatsiya qilish",
    )
    parser.add_argument(
        "--kiosk",
        action="store_true",
        help="Fullscreen kiosk rejimida ishga tushirish (klaviatura cheklovlari bilan)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Faqat uskunalar va tizim pre-check diagnostikasini o'tkazish va chiqish",
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Konfiguratsiya fayli yo'li",
    )
    args = parser.parse_args()

    # Load and validate config
    config = SystemConfig.load_from_yaml(args.config)
    setup_logging(config.app.log_file, config.app.log_level)

    # Initialize Repository & Check Migrations
    repository = DatabaseRepository(config.storage.db_path)
    repository.sync_rules("config/rules.yaml")

    # Check for unfinished sessions on boot
    recovery_svc = SessionRecoveryService(repository, mode=config.security.power_loss_recovery_mode)
    recovery_svc.check_and_recover_on_boot()

    # Hardware & Services Initialization
    simulation_mode = args.simulate or (config.app.environment == "simulation")
    camera_service = MultiCameraService(config.cameras, simulation_mode=simulation_mode)
    camera_service.start_all()

    # Detector
    ai_detector = MockDetector(healthy=True)

    # Precheck-only mode
    if args.check:
        import time
        time.sleep(0.3)
        from driving_eval.hardware.calibration import CalibrationService
        from driving_eval.hardware.precheck import PrecheckService
        calibs = {
            "FRONT": CalibrationService.load("config/calibration/front_camera.json"),
            "REAR": CalibrationService.load("config/calibration/rear_camera.json"),
            "LEFT": CalibrationService.load("config/calibration/left_camera.json"),
            "RIGHT": CalibrationService.load("config/calibration/right_camera.json"),
        }
        precheck = PrecheckService(config, camera_service, ai_detector, repository, calibs)
        report = precheck.run_all_checks()
        camera_service.stop_all()
        print(f"Pre-check natijasi: {'MUVAFFAQIN' if report.passed else 'BLOKLANDI'}")
        for item in report.items:
            print(f"  [{'OK' if item.passed else 'FAIL'}] {item.name}: {item.details}")
        return 0 if report.passed else 1

    # Audio & Evidence
    audio_service = AudioService(config.audio, simulate_playback=simulation_mode)
    audio_service.start()

    evidence_recorder = EvidenceRecorder(
        config.storage.evidence_dir,
        repository,
        buffer_duration_seconds=config.storage.ring_buffer_seconds,
        fps=30,
    )
    storage_manager = StorageManager(config.storage, repository)

    # PySide6 GUI App
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    window = DrivingEvaluationApp(
        config=config,
        repository=repository,
        camera_service=camera_service,
        ai_detector=ai_detector,
        audio_service=audio_service,
        evidence_recorder=evidence_recorder,
        storage_manager=storage_manager,
        kiosk_mode=args.kiosk or config.ui.kiosk_mode,
    )

    window.show()

    try:
        ret = app.exec()
    finally:
        camera_service.stop_all()
        audio_service.stop()

    return ret


if __name__ == "__main__":
    sys.exit(main())
