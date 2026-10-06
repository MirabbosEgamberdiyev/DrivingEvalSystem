"""Unit tests for tracking, calibration, sensor fusion, visual odometry, and exercise detection."""

import numpy as np

from driving_eval.ai.detector_base import BoundingBox, Detection
from driving_eval.ai.exercise_detector import ExerciseDetector, ExerciseStatus
from driving_eval.ai.tracker import MultiCameraTracker, SimpleByteTracker, TrackState, calculate_iou
from driving_eval.core.config_schema import SystemConfig
from driving_eval.hardware.calibration import CalibrationService, MultiCameraCalibration
from driving_eval.hardware.sensor_fusion import (
    FusedVehicleState,
    GPSData,
    IMUData,
    OBDData,
    SensorFusionService,
    VisualOdometryEstimator,
)


def test_calculate_iou():
    b1 = BoundingBox(10, 10, 50, 50)
    b2 = BoundingBox(10, 10, 50, 50)
    assert calculate_iou(b1, b2) == 1.0

    b3 = BoundingBox(100, 100, 200, 200)
    assert calculate_iou(b1, b3) == 0.0

    b4 = BoundingBox(30, 30, 50, 50)
    iou = calculate_iou(b1, b4)
    assert 0.0 < iou < 1.0


def test_tracker_preserves_id():
    tracker = SimpleByteTracker(iou_threshold=0.3)
    t0 = 1000.0

    d1 = Detection("cone", 0.9, BoundingBox(10, 10, 40, 40), "FRONT", t0)
    res1 = tracker.update([d1], t0)
    assert len(res1) == 1
    track_id = res1[0].track_id
    assert track_id is not None

    # Frame 2: slightly moved cone
    t1 = t0 + 0.033
    d2 = Detection("cone", 0.9, BoundingBox(12, 11, 42, 41), "FRONT", t1)
    res2 = tracker.update([d2], t1)
    assert len(res2) == 1
    assert res2[0].track_id == track_id  # Track ID MUST be preserved!


def test_bytetrack_low_confidence_retention():
    """ByteTrack 2nd stage matches low-confidence detection to preserve track ID through blur."""
    tracker = SimpleByteTracker(
        iou_threshold=0.3, high_threshold=0.5, low_threshold=0.15, min_hits_to_confirm=1
    )
    t0 = 100.0

    # Initial high-confidence detection (0.85)
    d1 = Detection("cone", 0.85, BoundingBox(50, 50, 90, 90), "FRONT", t0)
    res1 = tracker.update([d1], t0)
    track_id = res1[0].track_id
    assert track_id is not None

    # Subsequent frame: confidence dips to 0.25 (below high_threshold 0.50, but above low_threshold 0.15)
    t1 = t0 + 0.033
    d2 = Detection("cone", 0.25, BoundingBox(52, 51, 92, 91), "FRONT", t1)
    res2 = tracker.update([d2], t1)

    assert len(res2) == 1
    assert res2[0].track_id == track_id  # Matched in Stage 2 without dropping or creating new track!


def test_bytetrack_tentative_to_confirmed_lifecycle():
    tracker = SimpleByteTracker(min_hits_to_confirm=2)
    t = 10.0

    # First hit -> TENTATIVE
    d1 = Detection("cone", 0.9, BoundingBox(20, 20, 60, 60), "FRONT", t)
    res1 = tracker.update([d1], t)
    assert res1[0].metadata["track_state"] == TrackState.TENTATIVE.value
    assert tracker.is_confirmed(res1[0].track_id) is False

    # Second hit -> CONFIRMED
    t += 0.033
    d2 = Detection("cone", 0.9, BoundingBox(21, 20, 61, 60), "FRONT", t)
    res2 = tracker.update([d2], t)
    assert res2[0].metadata["track_state"] == TrackState.CONFIRMED.value
    assert tracker.is_confirmed(res2[0].track_id) is True


def test_bytetrack_coordinate_smoothing():
    tracker = SimpleByteTracker(smooth_alpha=0.5)
    t = 1.0

    d1 = Detection("cone", 0.9, BoundingBox(10.0, 10.0, 30.0, 30.0), "FRONT", t)
    tracker.update([d1], t)

    # Abrupt single-frame jitter in input box
    t += 0.033
    d2 = Detection("cone", 0.9, BoundingBox(14.0, 10.0, 34.0, 30.0), "FRONT", t)
    res2 = tracker.update([d2], t)

    # Box coordinates should be smoothed (0.5 * 14.0 + 0.5 * 10.0 = 12.0)
    assert abs(res2[0].bbox.x1 - 12.0) < 0.1


def test_multi_camera_tracker():
    multi_tracker = MultiCameraTracker(cameras=("FRONT", "REAR"))
    t = 50.0

    d_front = Detection("cone", 0.8, BoundingBox(10, 10, 30, 30), "FRONT", t)
    d_rear = Detection("car", 0.85, BoundingBox(100, 100, 200, 200), "REAR", t)

    results = multi_tracker.update_all(
        {"FRONT": [d_front], "REAR": [d_rear]}, timestamp=t
    )
    assert len(results["FRONT"]) == 1
    assert len(results["REAR"]) == 1
    assert results["FRONT"][0].track_id is not None
    assert results["REAR"][0].track_id is not None


def test_calibration_bev_and_roundtrip():
    cal = CalibrationService.load("config/calibration/front_camera.json")

    # Synthetic black frame
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    bev = cal.generate_bev_image(frame, output_size=(640, 640))
    assert bev.shape == (640, 640, 3)

    # Bidirectional projection roundtrip: pixel -> ground meters -> pixel
    px_orig, py_orig = 640.0, 480.0
    gx, gy = cal.pixel_to_ground_plane(px_orig, py_orig)
    px_rec, py_rec = cal.ground_to_pixel(gx, gy)

    assert abs(px_rec - px_orig) < 0.5
    assert abs(py_rec - py_orig) < 0.5


def test_calibration_polygon_and_line_distance():
    cal = CalibrationService.load("config/calibration/front_camera.json")

    # Project bounding box base to ground plane
    pts_px = [(400.0, 500.0), (500.0, 500.0), (500.0, 600.0), (400.0, 600.0)]
    pts_ground = cal.project_polygon_to_ground(pts_px)
    assert len(pts_ground) == 4

    # Distance to ground line
    point_g = (2.0, 5.0)
    line_start_g = (0.0, 5.0)
    line_end_g = (5.0, 5.0)
    dist = cal.point_to_line_distance_ground(point_g, line_start_g, line_end_g)
    assert abs(dist - 0.0) < 1e-4

    dist_off = cal.point_to_line_distance_ground((2.0, 6.0), line_start_g, line_end_g)
    assert abs(dist_off - 1.0) < 1e-4


def test_calibration_drift_verification():
    cal = CalibrationService.load("config/calibration/front_camera.json")

    # Exact expected fiducials -> passed
    fid_ok = {
        "hood_left_corner": (320, 680),
        "hood_right_corner": (960, 680),
    }
    passed, max_drift, details = cal.verify_fiducial_drift(fid_ok, max_drift_threshold_px=15.0)
    assert passed is True
    assert max_drift == 0.0
    assert len(details) == 0

    # Shifted fiducial -> failed
    fid_shifted = {
        "hood_left_corner": (320 + 25, 680),
        "hood_right_corner": (960, 680),
    }
    passed_s, max_drift_s, details_s = cal.verify_fiducial_drift(fid_shifted, max_drift_threshold_px=15.0)
    assert passed_s is False
    assert max_drift_s >= 25.0
    assert len(details_s) == 1
    assert "hood_left_corner" in details_s[0]


def test_multi_camera_calibration_loader():
    multi_cal = MultiCameraCalibration.load_from_dir("config/calibration")
    for cam in ("FRONT", "REAR", "LEFT", "RIGHT"):
        cal = multi_cal.get_calibration(cam)
        assert cal is not None
        assert cal.pixels_per_meter > 0


def test_visual_odometry_estimator():
    vo = VisualOdometryEstimator()
    frame1 = np.ones((720, 1280, 3), dtype=np.uint8) * 100
    res1 = vo.estimate_motion(frame1, timestamp=1.0)
    assert res1.speed_kmh == 0.0

    # Simulated motion test
    res_sim = vo.simulate_motion(speed_kmh=20.0, dt=0.1, timestamp=1.1)
    assert res_sim.speed_kmh == 20.0
    assert res_sim.displacement_m > 0.0


def test_sensor_fusion():
    fusion = SensorFusionService(speed_stop_threshold_kmh=1.5)
    t = 100.0

    # OBD active with speed 25 km/h
    fusion.update_obd(
        OBDData(
            speed_kmh=25.0,
            engine_rpm=2000,
            seatbelt_fastened=True,
            handbrake_active=False,
            turn_signal_left=False,
            turn_signal_right=False,
            timestamp=t,
        )
    )
    state = fusion.get_fused_state(t)
    assert state.speed_kmh == 25.0
    assert state.is_stopped is False
    assert state.seatbelt_fastened is True
    assert state.source_quality == "OBD_PRIMARY"

    # Vehicle stops (speed 0.5 km/h)
    fusion.update_obd(
        OBDData(
            speed_kmh=0.5,
            engine_rpm=800,
            seatbelt_fastened=True,
            handbrake_active=True,
            turn_signal_left=False,
            turn_signal_right=False,
            timestamp=t + 1.0,
        )
    )
    state_stopped = fusion.get_fused_state(t + 1.0)
    assert state_stopped.is_stopped is True
    assert state_stopped.handbrake_active is True


def test_sensor_fusion_gps_dropout_dead_reckoning():
    """When OBD and GPS drop out, sensor fusion smoothly falls back to Visual Odometry Dead Reckoning."""
    fusion = SensorFusionService()
    t = 200.0

    # Initially valid GPS
    gps = GPSData(lat=41.311081, lon=69.240562, speed_kmh=30.0, heading_deg=90.0, fix_valid=True, timestamp=t)
    fusion.update_gps(gps)
    st = fusion.get_fused_state(t)
    assert st.source_quality == "GPS_FALLBACK"

    # Now GPS drops out (t + 3.0s, old GPS timed out)
    t_dropout = t + 3.0
    vo_data = VisualOdometryEstimator().simulate_motion(speed_kmh=25.0, dt=0.5, timestamp=t_dropout)
    fusion.update_visual_odometry(vo_data)

    st_vo = fusion.get_fused_state(t_dropout)
    assert st_vo.source_quality == "VO_DEAD_RECKONING"
    assert st_vo.speed_kmh == 25.0
    # Longitude should have propagated eastward due to 90 deg heading
    assert st_vo.lon > gps.lon


def test_sensor_fusion_estakada_rollback_accumulation():
    fusion = SensorFusionService()
    t = 10.0

    # Incline detected (pitch > 5 deg) and negative longitudinal acceleration (rolling back)
    imu_slope = IMUData(
        accel_x=0.0,
        accel_y=-0.50,  # Negative accel = roll back
        accel_z=9.8,
        pitch_deg=8.5,  # Slope angle
        roll_deg=0.0,
        yaw_rate=0.0,
        timestamp=t,
    )
    fusion.update_imu(imu_slope)
    _ = fusion.get_fused_state(t)

    t += 0.5
    imu_slope.timestamp = t
    fusion.update_imu(imu_slope)
    st2 = fusion.get_fused_state(t)

    assert st2.rollback_distance_meters > 0.0
    assert fusion.is_rollback_exceeded(threshold_meters=0.05) is True


def test_exercise_detector_sequence_and_finish():
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    detector = ExerciseDetector(cfg.exercises)

    assert detector.current_exercise == "START"

    # Step to next exercise: ESTAKADA
    estakada_zone = detector._zones["ESTAKADA"]
    st1 = FusedVehicleState(
        timestamp=1.0, speed_kmh=15.0, is_stopped=False, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=False, turn_signal_active=False,
        lat=estakada_zone.lat, lon=estakada_zone.lon, rollback_distance_meters=0.0, source_quality="OK"
    )
    current, violation, msg = detector.update_location(st1)
    assert current == "ESTAKADA"
    assert violation is False

    # Skip all the way to STOP (bypassing ZMEIKA, TURN_90, PARALLEL_PARKING, GARAGE_REVERSE)
    stop_zone = detector._zones["STOP"]
    st_skip = FusedVehicleState(
        timestamp=2.0, speed_kmh=15.0, is_stopped=False, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=False, turn_signal_active=False,
        lat=stop_zone.lat, lon=stop_zone.lon, rollback_distance_meters=0.0, source_quality="OK"
    )
    current, violation, msg = detector.update_location(st_skip)
    assert violation is True
    assert "buzildi" in msg
    assert detector.exercise_statuses["ZMEIKA"] == ExerciseStatus.SKIPPED

    # Arrive at FINISH and test finalization permission
    detector.force_set_exercise("FINISH")
    finish_zone = detector._zones["FINISH"]
    st_finish_moving = FusedVehicleState(
        timestamp=3.0, speed_kmh=10.0, is_stopped=False, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=False, turn_signal_active=False,
        lat=finish_zone.lat, lon=finish_zone.lon, rollback_distance_meters=0.0, source_quality="OK"
    )
    assert detector.can_finalize_test(st_finish_moving) is False

    # Vehicle stops in finish zone -> CAN finalize now!
    st_finish_stopped = FusedVehicleState(
        timestamp=4.0, speed_kmh=0.0, is_stopped=True, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=True, turn_signal_active=False,
        lat=finish_zone.lat, lon=finish_zone.lon, rollback_distance_meters=0.0, source_quality="OK"
    )
    assert detector.can_finalize_test(st_finish_stopped) is True


def test_exercise_detector_active_rules_and_heading():
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    detector = ExerciseDetector(cfg.exercises)

    # In START: seatbelt and start signal active
    assert detector.is_rule_active_for_current_exercise("SEATBELT_UNFASTENED") is True
    assert detector.is_rule_active_for_current_exercise("START_SIGNAL_OMITTED") is True
    # Estakada rollback rule must NOT be active during START
    assert detector.is_rule_active_for_current_exercise("ESTAKADA_ROLLBACK", rule_bound_exercise="ESTAKADA") is False

    # Move to ESTAKADA
    detector.force_set_exercise("ESTAKADA")
    assert detector.is_rule_active_for_current_exercise("ESTAKADA_ROLLBACK", rule_bound_exercise="ESTAKADA") is True

    # Heading check
    assert detector.check_heading("ESTAKADA", current_heading_deg=10.0) is True
    assert detector.check_heading("ESTAKADA", current_heading_deg=180.0) is False
