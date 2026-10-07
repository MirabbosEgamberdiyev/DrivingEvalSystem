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
    assert scoring.is_passing is False
    assert scoring.is_terminated is False



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
    assert scoring.is_passing is True
    assert scoring.is_terminated is False



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


def test_processed_event_multilingual_passports(empty_state):
    """ProcessedViolationEvent provides text and audio files across all 3 languages."""
    engine = RuleEngine()
    det = Detection(
        label="cone",
        confidence=0.95,
        bbox=BoundingBox(500, 600, 550, 690),
        camera="FRONT",
        timestamp=100.0,
        track_id=10,
    )

    ev = None
    for i in range(6):
        ctx = EvaluationContext(
            timestamp=100.0 + i * 0.033,
            current_exercise="ZMEIKA",
            vehicle_state=empty_state,
            detections=[det],
            frame_bundle=None,
            calibrations={},
        )
        evs = engine.evaluate(ctx)
        if evs:
            ev = evs[0]
            break

    assert ev is not None
    assert ev.get_title("uz-Latn") == "Yo'l belgilovchi konusga tegish"
    assert ev.get_title("uz-Cyrl") == "Йўл белгиловчи конусга тегиш"
    assert ev.get_title("ru") == "Касание разметочного конуса"

    assert "Konusga" in ev.get_screen_text("uz-Latn")
    assert "Конусга" in ev.get_screen_text("uz-Cyrl")
    assert "конуса" in ev.get_screen_text("ru")

    assert ev.get_voice_file("uz-Latn") == "cone_touch.wav"


def test_debounce_resets_on_interrupted_flicker(empty_state):
    """A 2-frame glitch must not trigger violation if debounce is 5 frames."""
    engine = RuleEngine()
    det = Detection(
        label="cone",
        confidence=0.95,
        bbox=BoundingBox(500, 600, 550, 690),
        camera="FRONT",
        timestamp=100.0,
        track_id=88,
    )

    # Frame 1 & 2: detected
    for i in range(2):
        ctx = EvaluationContext(
            timestamp=100.0 + i * 0.033,
            current_exercise="ZMEIKA",
            vehicle_state=empty_state,
            detections=[det],
            frame_bundle=None,
            calibrations={},
        )
        events = engine.evaluate(ctx)
        assert len(events) == 0

    # Frame 3: no detection (glitch ended)
    ctx_empty = EvaluationContext(
        timestamp=100.0 + 2 * 0.033,
        current_exercise="ZMEIKA",
        vehicle_state=empty_state,
        detections=[],
        frame_bundle=None,
        calibrations={},
    )
    events = engine.evaluate(ctx_empty)
    assert len(events) == 0


def test_distinct_tracks_emit_separate_violations(empty_state):
    """Two different cones touched in same exercise emit separate violations."""
    engine = RuleEngine()
    scoring = ScoringEngine(ScoringConfig(start_score=100, pass_score=80))

    # Cone 1
    d1 = Detection("cone", 0.95, BoundingBox(100, 500, 150, 690), "FRONT", 100.0, track_id=1)
    for i in range(6):
        ctx = EvaluationContext(
            timestamp=100.0 + i * 0.033,
            current_exercise="ZMEIKA",
            vehicle_state=empty_state,
            detections=[d1],
            frame_bundle=None,
            calibrations={},
        )
        for ev in engine.evaluate(ctx):
            scoring.apply_event(ev)

    assert scoring.current_score == 75

    # Cone 2 (different track_id = 2)
    d2 = Detection("cone", 0.95, BoundingBox(600, 500, 650, 690), "FRONT", 101.0, track_id=2)
    for i in range(6):
        ctx = EvaluationContext(
            timestamp=101.0 + i * 0.033,
            current_exercise="ZMEIKA",
            vehicle_state=empty_state,
            detections=[d2],
            frame_bundle=None,
            calibrations={},
        )
        for ev in engine.evaluate(ctx):
            scoring.apply_event(ev)

    assert scoring.current_score == 50  # 100 - 25 - 25
    assert scoring.confirmed_violations_count == 2 if hasattr(scoring, 'confirmed_violations_count') else len(scoring.confirmed_violations) == 2


def test_all_rule_plugins_registered():
    engine = RuleEngine()
    registered_codes = set(engine._plugins.keys())
    manifest_codes = {r.code for r in engine.manifest.rules}

    # All 9 rules in rules.yaml must have registered evaluator plugins
    assert manifest_codes == registered_codes


def test_scoring_engine_pass_fail_boundary_conditions():
    """Validates boundary conditions: 100, 80 (exact pass), 79 (fail), and critical termination."""
    from driving_eval.rules.event_manager import ProcessedViolationEvent

    cfg = ScoringConfig(start_score=100, pass_score=80)
    scoring = ScoringEngine(cfg)

    # Initial state
    assert scoring.current_score == 100
    assert scoring.is_passing is True
    assert scoring.is_terminated is False

    def make_event(v_id: str, code: str, penalty: int, critical: bool = False):
        return ProcessedViolationEvent(
            violation_id=v_id,
            rule_code=code,
            status="CONFIRMED",
            confidence=0.9,
            penalty=penalty,
            critical=critical,
            camera="FRONT",
            exercise="START",
            details="Boundary test violation",
            screen_text="Test screen text",
            voice_file="test.wav",
            voice_text="Test voice text",
            timestamp=100.0,
        )

    # Apply 10 penalty points -> score 90 >= 80 -> PASS
    ev10 = make_event("EV-1", "SEATBELT_UNFASTENED", penalty=10)
    scoring.apply_event(ev10)
    assert scoring.current_score == 90
    assert scoring.is_passing is True
    assert scoring.is_terminated is False

    # Apply 10 more penalty points -> score 80 == pass_score -> EXACT BOUNDARY PASS
    scoring.apply_event(make_event("EV-2", "SEATBELT_UNFASTENED", penalty=10))
    assert scoring.current_score == 80
    assert scoring.is_passing is True
    assert scoring.is_terminated is False

    # Apply 1 more penalty point -> score 79 < 80 -> FAIL
    scoring.apply_event(make_event("EV-3", "INDICATOR_MISSED", penalty=1))
    assert scoring.current_score == 79
    assert scoring.is_passing is False
    assert scoring.is_terminated is False

    # Critical violation causes immediate termination and fail regardless of score
    scoring_crit = ScoringEngine(cfg)
    ev_crit = make_event("EV-4", "CRITICAL_COLLISION", penalty=100, critical=True)
    scoring_crit.apply_event(ev_crit)
    assert scoring_crit.is_terminated is True
    assert scoring_crit.is_passing is False


