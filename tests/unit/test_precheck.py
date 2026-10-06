"""Unit tests for PrecheckService (hardware, cameras, AI, calibration, DB)."""

import time

import pytest

from driving_eval.ai.mock_detector import MockDetector
from driving_eval.core.config_schema import SystemConfig
from driving_eval.db.repository import DatabaseRepository
from driving_eval.hardware.calibration import CalibrationService
from driving_eval.hardware.camera_service import MultiCameraService
from driving_eval.hardware.precheck import PrecheckService


@pytest.fixture
def test_env(tmp_path):
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    # Point DB and storage to temp path, lower min_free_disk_gb for testing
    cfg.storage.db_path = str(tmp_path / "precheck.db")
    cfg.storage.base_dir = str(tmp_path / "data")
    cfg.storage.min_free_disk_gb = 1.0

    repo = DatabaseRepository(cfg.storage.db_path)
    detector = MockDetector(healthy=True)
    cam_service = MultiCameraService(cfg.cameras, simulation_mode=True)
    cam_service.start_all()
    time.sleep(0.3)

    calibs = {
        "FRONT": CalibrationService.load("config/calibration/front_camera.json"),
        "REAR": CalibrationService.load("config/calibration/rear_camera.json"),
        "LEFT": CalibrationService.load("config/calibration/left_camera.json"),
        "RIGHT": CalibrationService.load("config/calibration/right_camera.json"),
    }

    service = PrecheckService(
        config=cfg,
        camera_service=cam_service,
        ai_detector=detector,
        repository=repo,
        calibrations=calibs,
    )

    yield service, cam_service, detector, calibs
    cam_service.stop_all()


def test_precheck_all_passed(test_env):
    service, cam_service, detector, calibs = test_env
    report = service.run_all_checks()
    assert report.passed is True
    assert len(report.block_reasons) == 0


def test_precheck_fails_on_camera_offline(test_env):
    service, cam_service, detector, calibs = test_env
    # Disconnect LEFT camera
    cam_service.workers["LEFT"].stop()

    report = service.run_all_checks()
    assert report.passed is False
    assert any("LEFT" in r for r in report.block_reasons)


def test_precheck_fails_on_ai_engine_failure(test_env):
    service, cam_service, detector, calibs = test_env
    detector.set_healthy(False)

    report = service.run_all_checks()
    assert report.passed is False
    assert any("AI" in r for r in report.block_reasons)


def test_precheck_fails_on_calibration_drift(test_env):
    service, cam_service, detector, calibs = test_env
    # Inject 35 px drift on FRONT fiducial
    drift_map = {
        "FRONT": {
            "hood_left_corner": (320 + 35, 680),
            "hood_right_corner": (960, 680),
        }
    }

    report = service.run_all_checks(detected_fiducials_map=drift_map)
    assert report.passed is False
    assert any("FRONT" in r and "siljishi" in r for r in report.block_reasons)
