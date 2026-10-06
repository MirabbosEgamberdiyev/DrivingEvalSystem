"""Unit tests for Serial NMEA GPS, ELM327 OBD-II, and Camera Calibration utilities."""


from driving_eval.core.config_schema import CameraCalibration
from driving_eval.hardware.gps_serial_reader import parse_nmea_rmc
from driving_eval.hardware.obd_serial_reader import (
    parse_elm327_rpm_response,
    parse_elm327_speed_response,
)
from tools.auto_calibrate_cameras import compute_ground_homography, save_camera_calibration


def test_parse_nmea_rmc_valid_and_void():
    # Valid RMC sentence: 41 deg 18.665 min N, 69 deg 14.433 min E, 15.5 knots (28.71 km/h), heading 90.0 deg
    sample_valid = "$GPRMC,123519,A,4118.665,N,06914.433,E,15.5,90.0,061026,,,A*77"
    gps = parse_nmea_rmc(sample_valid)
    assert gps is not None
    assert gps.fix_valid is True
    assert round(gps.lat, 3) == 41.311
    assert round(gps.lon, 3) == 69.241
    assert gps.speed_kmh == 28.71
    assert gps.heading_deg == 90.0

    # Void (no satellite lock) RMC sentence
    sample_void = "$GPRMC,123519,V,,,,,,,061026,,,N*48"
    gps_void = parse_nmea_rmc(sample_void)
    assert gps_void is not None
    assert gps_void.fix_valid is False
    assert gps_void.lat == 0.0


def test_parse_elm327_speed_and_rpm():
    # Speed: PID 010D returns 0x32 (50 km/h)
    resp_speed = "41 0D 32"
    assert parse_elm327_speed_response(resp_speed) == 50.0

    # RPM: PID 010C returns 0x1F 0x40 (8000 / 4 = 2000 RPM)
    resp_rpm = "41 0C 1F 40"
    assert parse_elm327_rpm_response(resp_rpm) == 2000


def test_auto_calibrate_homography_and_schema_validation(tmp_path):
    img_pts = [
        (450.0, 600.0),
        (1470.0, 600.0),
        (1700.0, 980.0),
        (220.0, 980.0),
    ]
    ground_m = [
        (-1.5, 5.0),
        (1.5, 5.0),
        (1.5, 1.5),
        (-1.5, 1.5),
    ]

    h_matrix, ppm = compute_ground_homography(img_pts, ground_m, pixels_per_meter=100.0)
    assert len(h_matrix) == 3
    assert len(h_matrix[0]) == 3
    assert ppm == 100.0

    out_file = tmp_path / "test_cam.json"
    save_camera_calibration(out_file, "FRONT", h_matrix, ppm)
    assert out_file.exists()

    # Verify that saved calibration adheres 100% to CameraCalibration pydantic schema
    loaded = CameraCalibration.load_from_json(out_file)
    assert loaded.camera_name == "FRONT"
    assert loaded.resolution == [1920, 1080]
    assert len(loaded.homography_matrix) == 3
