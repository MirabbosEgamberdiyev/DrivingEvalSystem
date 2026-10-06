"""Unit tests for Rule Engine, Event Dedup, Scoring, Critical flows, and SUSPECT mechanism."""

import pytest

from driving_eval.ai.detector_base import BoundingBox, Detection
from driving_eval.core.config_schema import ScoringConfig
from driving_eval.hardware.sensor_fusion import FusedVehicleState
from driving_eval.rules.base_rule import EvaluationContext
from driving_eval.rules.engine import RuleEngine
from driving_eval.rules.scoring import ScoringEngine


@pytest.fixture
def empty_state():
    return FusedVehicleState(
        timestamp=100.0, speed_kmh=10.0, is_stopped=False, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=False, turn_signal_active=True,
        lat=41.311, lon=69.240, rollback_distance_meters=0.0, source_quality="OK"
    )


def test_20_frames_single_cone_touch_yields_exactly_one_event(empty_state):
    engine = RuleEngine()
    scoring = ScoringEngine(ScoringConfig(start_score=100, pass_score=80))

    events_received = []

    # Simulate 20 consecutive frames of cone touching vehicle (y2=690, confidence=0.95)
    for frame_idx in range(20):
        t = 100.0 + (frame_idx * 0.033)
        det = Detection(
            label="cone",
            confidence=0.95,
            bbox=BoundingBox(500, 600, 550, 690),
            camera="FRONT",
            timestamp=t,
            track_id=42,  # Same tracked cone
        )
        ctx = EvaluationContext(
            timestamp=t,
            current_exercise="ZMEIKA",
            vehicle_state=empty_state,
            detections=[det],
            frame_bundle=None,
            calibrations={},
        )
        events = engine.evaluate(ctx)
        for ev in events:
            events_received.append(ev)
            scoring.apply_event(ev)

    # 20 frames MUST result in EXACTLY 1 event!
    assert len(events_received) == 1
    event = events_received[0]
    assert event.rule_code == "CONE_TOUCH"
    assert event.status == "CONFIRMED"
    assert event.penalty == 25
    assert scoring.current_score == 75
    assert scoring.total_penalty == 25


def test_low_confidence_produces_suspect_with_zero_penalty(empty_state):
    engine = RuleEngine()
    scoring = ScoringEngine(ScoringConfig(start_score=100, pass_score=80))

    events_received = []

    # Simulate frames with low confidence (0.65 < min_confidence 0.80)
    for frame_idx in range(10):
        t = 100.0 + (frame_idx * 0.033)
        det = Detection(
            label="cone",
            confidence=0.65,  # Low confidence
            bbox=BoundingBox(500, 600, 550, 690),
            camera="FRONT",
            timestamp=t,
            track_id=101,
        )
        ctx = EvaluationContext(
            timestamp=t,
            current_exercise="ZMEIKA",
            vehicle_state=empty_state,
            detections=[det],
            frame_bundle=None,
            calibrations={},
        )
        events = engine.evaluate(ctx)
        for ev in events:
            events_received.append(ev)
            scoring.apply_event(ev)

    assert len(events_received) == 1
    event = events_received[0]
    assert event.status == "SUSPECT"
    assert event.penalty == 0
    # Score MUST NOT be penalized!
    assert scoring.current_score == 100
    assert scoring.total_penalty == 0
    assert len(scoring.suspect_events) == 1


def test_critical_violation_flow_causes_fail_and_termination(empty_state):
    engine = RuleEngine()
    scoring = ScoringEngine(ScoringConfig(start_score=100, pass_score=80))

    events_received = []

    # Simulate critical collision
    for frame_idx in range(5):
        t = 100.0 + (frame_idx * 0.033)
        det = Detection(
            label="barrier",
            confidence=0.95,
            bbox=BoundingBox(300, 400, 600, 700),
            camera="FRONT",
            timestamp=t,
            track_id=999,
        )
        ctx = EvaluationContext(
            timestamp=t,
            current_exercise="START",
            vehicle_state=empty_state,
            detections=[det],
            frame_bundle=None,
            calibrations={},
        )
        events = engine.evaluate(ctx)
        for ev in events:
            events_received.append(ev)
            scoring.apply_event(ev)

    assert len(events_received) == 1
    ev = events_received[0]
    assert ev.rule_code == "CRITICAL_COLLISION"
    assert ev.critical is True
    assert scoring.is_terminated is True
    assert scoring.is_passing is False


def test_exercise_binding_filters_inactive_rules(empty_state):
    engine = RuleEngine()

    # Cone touch in "START" exercise (CONE_TOUCH is bound only to ZMEIKA, PARALLEL_PARKING, etc.)
    det = Detection(
        label="cone",
        confidence=0.95,
        bbox=BoundingBox(500, 600, 550, 690),
        camera="FRONT",
        timestamp=100.0,
        track_id=1,
    )
    ctx = EvaluationContext(
        timestamp=100.0,
        current_exercise="START",
        vehicle_state=empty_state,
        detections=[det],
        frame_bundle=None,
        calibrations={},
    )
    events = engine.evaluate(ctx)
    # Should be empty because CONE_TOUCH is inactive during START!
    assert len(events) == 0
