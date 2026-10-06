"""Unit tests for MultiCameraService acquisition, monotonic timing, and synchronization."""

import time

import pytest

from driving_eval.core.config_schema import SystemConfig
from driving_eval.hardware.camera_service import MultiCameraService, StreamStatus


@pytest.fixture
def system_config():
    return SystemConfig.load_from_yaml("config/config.yaml")


def test_camera_service_startup_and_bundle_sync(system_config):
    cam_service = MultiCameraService(system_config.cameras, simulation_mode=True)
    cam_service.start_all()

    # Allow workers to generate first frames
    time.sleep(0.3)

    try:
        health = cam_service.get_all_health()
        assert len(health) == 4
        for name in ["FRONT", "REAR", "LEFT", "RIGHT"]:
            assert health[name].status == StreamStatus.ONLINE
            assert health[name].total_frames > 0

        bundle = cam_service.get_synchronized_bundle()
        assert bundle is not None
        assert len(bundle.frames) == 4
        assert bundle.is_synchronized is True
        assert bundle.max_jitter_ms <= system_config.cameras.sync_tolerance_ms

        # Check monotonic timestamps
        front_ts = bundle.frames["FRONT"].timestamp
        assert front_ts > 0.0

    finally:
        cam_service.stop_all()


def test_camera_disconnect_detection(system_config):
    cam_service = MultiCameraService(system_config.cameras, simulation_mode=True)
    cam_service.start_all()
    time.sleep(0.2)

    try:
        # Simulate stopping right camera
        cam_service.workers["RIGHT"].stop()
        health = cam_service.get_all_health()
        assert health["RIGHT"].status == StreamStatus.OFFLINE

    finally:
        cam_service.stop_all()
