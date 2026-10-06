"""Unit tests for PDF/CSV reporting and headless UI orchestration."""

import os

from driving_eval.ai.mock_detector import MockDetector
from driving_eval.audio.audio_service import AudioService
from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.state_machine import ExamState
from driving_eval.db.repository import DatabaseRepository
from driving_eval.evidence.recorder import EvidenceRecorder
from driving_eval.evidence.storage import StorageManager
from driving_eval.hardware.camera_service import MultiCameraService
from driving_eval.reporting.csv_report import export_violations_to_csv
from driving_eval.reporting.pdf_report import generate_pdf_report
from driving_eval.ui.app import DrivingEvaluationApp

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def test_pdf_and_csv_generation(tmp_path):
    session_data = {
        "id": "SESS-2026-TEST",
        "student_id": "STU-001",
        "started_at": "2026-10-06T10:00:00Z",
        "score": 75,
        "result": "FAIL",
        "rules_version": "1.0.0",
        "session_hash": "a" * 64,
    }
    student_data = {
        "first_name": "Nodir",
        "last_name": "Jalilov",
        "passport_id": "AA9876543",
    }
    vehicle_data = {
        "model": "Cobalt",
        "plate_number": "01 A 111 AA",
    }
    violations = [
        {
            "rule_code": "CONE_TOUCH",
            "title": "Konusga tegish",
            "status": "CONFIRMED",
            "penalty": 25,
            "critical": False,
            "confidence": 0.95,
            "camera": "FRONT",
            "exercise": "ZMEIKA",
            "timestamp": "2026-10-06T10:05:00Z",
            "description": "Konusga tegilishi",
        },
        {
            "rule_code": "STOP_LINE_VIOLATION",
            "title": "Stop chizig'i",
            "status": "SUSPECT",
            "penalty": 0,
            "critical": False,
            "confidence": 0.60,
            "camera": "FRONT",
            "exercise": "STOP",
            "timestamp": "2026-10-06T10:08:00Z",
            "description": "Shubhali chiziq kesilishi",
        },
    ]

    for lang in ("uz-Latn", "uz-Cyrl", "ru"):
        p_out = tmp_path / f"report_{lang}.pdf"
        c_out = tmp_path / f"report_{lang}.csv"
        res_pdf = generate_pdf_report(p_out, session_data, student_data, vehicle_data, violations, "a" * 64, language=lang)
        assert res_pdf.exists()
        assert res_pdf.stat().st_size > 1000

        res_csv = export_violations_to_csv(c_out, session_data, violations, language=lang)
        assert res_csv.exists()
        assert "CONE_TOUCH" in res_csv.read_text(encoding="utf-8-sig")


def test_app_ui_lifecycle_headless(qapp, tmp_path):
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    cfg.storage.db_path = str(tmp_path / "app.db")
    cfg.storage.base_dir = str(tmp_path / "data")
    cfg.storage.evidence_dir = str(tmp_path / "data" / "evidence")
    cfg.storage.min_free_disk_gb = 1.0

    repo = DatabaseRepository(cfg.storage.db_path)
    repo.sync_rules("config/rules.yaml")

    cam_service = MultiCameraService(cfg.cameras, simulation_mode=True)
    cam_service.start_all()
    detector = MockDetector(healthy=True)
    audio = AudioService(cfg.audio, simulate_playback=True)
    audio.start()
    recorder = EvidenceRecorder(cfg.storage.evidence_dir, repo, buffer_duration_seconds=2.0, fps=10)
    storage = StorageManager(cfg.storage, repo)

    app_win = DrivingEvaluationApp(
        config=cfg,
        repository=repo,
        camera_service=cam_service,
        ai_detector=detector,
        audio_service=audio,
        evidence_recorder=recorder,
        storage_manager=storage,
        kiosk_mode=False,
    )

    try:
        assert app_win.state_machine.current_state == ExamState.READY

        # Candidate clicks precheck
        app_win._start_precheck({"passport_id": "BB1112233", "first_name": "Test", "last_name": "User"})
        assert app_win.state_machine.current_state in (ExamState.SYSTEM_CHECK, ExamState.PRECHECK)

        # Proceed to test
        app_win._proceed_to_test_ready()
        assert app_win.state_machine.current_state == ExamState.TEST_ACTIVE

        # Run tick
        app_win._engine_tick()

        # Finish test
        app_win.exercise_detector.force_set_exercise("FINISH")
        app_win.state_machine._state = ExamState.VEHICLE_STOPPED
        app_win._finish_test()

        assert app_win.state_machine.current_state == ExamState.COMPLETED

    finally:
        cam_service.stop_all()
        audio.stop()
        app_win.close()


def test_app_runner_check_mode(monkeypatch):
    import sys

    from driving_eval.app_runner import main

    monkeypatch.setattr(sys, "argv", ["app_runner", "--simulate", "--check", "--config", "config/config.yaml"])
    ret = main()
    assert ret == 0

