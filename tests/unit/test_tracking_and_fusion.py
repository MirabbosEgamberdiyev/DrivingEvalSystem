"""Unit tests for tracking, sensor fusion, and exercise detection."""


from driving_eval.ai.detector_base import BoundingBox, Detection
from driving_eval.ai.exercise_detector import ExerciseDetector
from driving_eval.ai.tracker import SimpleByteTracker, calculate_iou
from driving_eval.core.config_schema import SystemConfig
from driving_eval.hardware.sensor_fusion import FusedVehicleState, OBDData, SensorFusionService


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


def test_sensor_fusion():
    fusion = SensorFusionService(speed_stop_threshold_kmh=1.5)
    t = 100.0

    # OBD active with speed 25 km/h
    fusion.update_obd(OBDData(speed_kmh=25.0, engine_rpm=2000, seatbelt_fastened=True, handbrake_active=False, turn_signal_left=False, turn_signal_right=False, timestamp=t))
    state = fusion.get_fused_state(t)
    assert state.speed_kmh == 25.0
    assert state.is_stopped is False
    assert state.seatbelt_fastened is True

    # Vehicle stops (speed 0.5 km/h)
    fusion.update_obd(OBDData(speed_kmh=0.5, engine_rpm=800, seatbelt_fastened=True, handbrake_active=True, turn_signal_left=False, turn_signal_right=False, timestamp=t + 1.0))
    state_stopped = fusion.get_fused_state(t + 1.0)
    assert state_stopped.is_stopped is True
    assert state_stopped.handbrake_active is True


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

    # Arrive at FINISH and test finalization permission
    detector.force_set_exercise("FINISH")
    finish_zone = detector._zones["FINISH"]
    st_finish_moving = FusedVehicleState(
        timestamp=3.0, speed_kmh=10.0, is_stopped=False, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=False, turn_signal_active=False,
        lat=finish_zone.lat, lon=finish_zone.lon, rollback_distance_meters=0.0, source_quality="OK"
    )
    # Moving in finish zone -> Cannot finalize yet
    assert detector.can_finalize_test(st_finish_moving) is False

    # Vehicle stops in finish zone -> CAN finalize now!
    st_finish_stopped = FusedVehicleState(
        timestamp=4.0, speed_kmh=0.0, is_stopped=True, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=True, turn_signal_active=False,
        lat=finish_zone.lat, lon=finish_zone.lon, rollback_distance_meters=0.0, source_quality="OK"
    )
    assert detector.can_finalize_test(st_finish_stopped) is True
