"""Integration test guaranteeing strict 100% offline runtime isolation.

Blocks any network socket connections and verifies that the entire driving evaluation
system runs without attempting any internet, cloud, or remote telemetry call.
"""

import socket

from driving_eval.ai.mock_detector import MockDetector
from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.state_machine import ExamState, ExamStateMachine
from driving_eval.db.repository import DatabaseRepository
from driving_eval.hardware.camera_service import MultiCameraService
from driving_eval.hardware.precheck import PrecheckService
from driving_eval.rules.scoring import ScoringEngine


def test_runtime_offline_isolation_with_blocked_sockets(monkeypatch, tmp_path):
    """Guarantees zero network calls during runtime execution."""

    def blocked_socket(*args, **kwargs):
        raise RuntimeError("TARMOQ CHAQIRUVI TAQIQLANGAN! 100% offline qoidasi buzildi.")

    def blocked_connect(*args, **kwargs):
        raise RuntimeError("TARMOQQA ULANISH TAQIQLANGAN! 100% offline qoidasi buzildi.")

    # Block socket constructor and connect
    monkeypatch.setattr(socket, "socket", blocked_socket)
    monkeypatch.setattr(socket, "create_connection", blocked_connect)

    # Now execute complete core lifecycle under network lockdown
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    cfg.storage.db_path = str(tmp_path / "offline_test.db")
    cfg.storage.base_dir = str(tmp_path / "data")
    cfg.storage.min_free_disk_gb = 1.0

    repo = DatabaseRepository(cfg.storage.db_path)
    repo.sync_rules("config/rules.yaml")

    cam_service = MultiCameraService(cfg.cameras, simulation_mode=True)
    cam_service.start_all()
    import time
    time.sleep(0.3)

    try:
        detector = MockDetector(healthy=True)
        precheck = PrecheckService(cfg, cam_service, detector, repo, {})
        report = precheck.run_all_checks()
        assert report.passed is True

        sm = ExamStateMachine(repository=repo)
        sm.transition_to(ExamState.BOOT)
        sm.transition_to(ExamState.READY)
        sm.transition_to(ExamState.PRECHECK)
        sm.transition_to(ExamState.CAMERA_CHECK)
        sm.transition_to(ExamState.SYSTEM_CHECK)
        sm.transition_to(ExamState.TEST_READY)
        sm.transition_to(ExamState.TEST_ACTIVE)

        # Run scoring
        scoring = ScoringEngine(cfg.scoring)
        assert scoring.current_score == 100

        # Terminate
        sm.transition_to(ExamState.FINISH_DETECTED)
        sm.transition_to(ExamState.VEHICLE_STOPPED)
        sm.transition_to(ExamState.FINALIZING)
        sm.transition_to(ExamState.RESULT_READY)
        sm.transition_to(ExamState.COMPLETED)
        assert sm.current_state == ExamState.COMPLETED

    finally:
        cam_service.stop_all()
