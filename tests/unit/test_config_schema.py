"""Unit tests for configuration schema validation (config.yaml, rules.yaml, car.yaml, calibration)."""

from pathlib import Path

import pytest

from driving_eval.core.config_schema import (
    CameraCalibration,
    CarConfig,
    RulesManifest,
    SystemConfig,
)
from driving_eval.core.exceptions import ConfigurationError, RulesValidationError


def test_system_config_load_valid():
    config_path = Path("config/config.yaml")
    assert config_path.exists()
    cfg = SystemConfig.load_from_yaml(config_path)
    assert cfg.app.name == "Standalone 4-Camera Offline AI Driving Evaluation System"
    assert cfg.scoring.start_score == 100
    assert cfg.scoring.pass_score == 80
    assert len(cfg.cameras.devices) == 4
    assert "front" in cfg.cameras.devices
    assert cfg.storage.min_free_disk_gb == 10.0


def test_system_config_missing_camera_fails(tmp_path):
    bad_cfg = tmp_path / "bad_config.yaml"
    bad_cfg.write_text("""
app:
  name: "Test"
  version: "1.0"
  rules_version: "1.0"
scoring:
  start_score: 100
  pass_score: 80
cameras:
  devices: {}
""", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        SystemConfig.load_from_yaml(bad_cfg)


def test_system_config_n_camera_flexibility():
    from driving_eval.core.config_schema import CamerasConfig
    cameras_dict = {
        "sync_tolerance_ms": 66.0,
        "min_operational_fps": 20.0,
        "max_drift_threshold_px": 15.0,
        "devices": {
            "front": {"name": "FRONT", "device_index": 0},
            "cabin": {"name": "CABIN", "device_index": 1},
        },
    }
    cfg = CamerasConfig.model_validate(cameras_dict)
    assert len(cfg.devices) == 2
    assert "front" in cfg.devices
    assert "cabin" in cfg.devices
    assert cfg.devices["cabin"].name == "CABIN"


def test_rules_manifest_load_valid():
    rules_path = Path("config/rules.yaml")
    assert rules_path.exists()
    manifest = RulesManifest.load_from_yaml(rules_path)
    assert len(manifest.rules) >= 5
    seatbelt = manifest.get_rule("SEATBELT_UNFASTENED")
    assert seatbelt is not None
    assert seatbelt.penalty == 10
    assert not seatbelt.critical
    collision = manifest.get_rule("CRITICAL_COLLISION")
    assert collision is not None
    assert collision.critical is True


def test_rules_manifest_duplicate_code_fails(tmp_path):
    bad_yaml = tmp_path / "bad_rules.yaml"
    bad_yaml.write_text("""
version: "1.0"
last_updated: "2026-10-06"
rules:
  - code: "RULE_DUP"
    title: "Title 1"
    screen_text: "Text 1"
    voice_file: "1.wav"
    voice_text: "Ovoz 1"
    penalty: 10
  - code: "RULE_DUP"
    title: "Title 2"
    screen_text: "Text 2"
    voice_file: "2.wav"
    voice_text: "Ovoz 2"
    penalty: 20
""", encoding="utf-8")

    with pytest.raises(RulesValidationError, match="takrorlangan qoida"):
        RulesManifest.load_from_yaml(bad_yaml)


def test_car_config_load_valid():
    car_path = Path("config/car.yaml")
    assert car_path.exists()
    car = CarConfig.load_from_yaml(car_path)
    assert car.car_id == "CAR-UZ-01"
    assert car.dimensions_meters.length > 4.0


def test_calibration_load_valid():
    calib_path = Path("config/calibration/front_camera.json")
    assert calib_path.exists()
    calib = CameraCalibration.load_from_json(calib_path)
    assert calib.camera_name == "FRONT"
    assert calib.pixels_per_meter > 0.0
    assert len(calib.reference_fiducials) >= 1
