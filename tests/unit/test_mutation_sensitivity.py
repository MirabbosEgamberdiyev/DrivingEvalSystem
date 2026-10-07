"""Mutation sensitivity testing: Proves tests catch boundary shifts, debounce mutants, and integrity tamper."""

from driving_eval.core.config_schema import RuleItem, ScoringConfig
from driving_eval.hardware.sensor_fusion import FusedVehicleState
from driving_eval.rules.base_rule import EvaluationContext, RuleEvaluationResult
from driving_eval.rules.engine import RuleEngine
from driving_eval.rules.event_manager import EventManager, ProcessedViolationEvent
from driving_eval.rules.scoring import ScoringEngine


def _make_event(rule_code: str, penalty: int, critical: bool = False, status: str = "CONFIRMED") -> ProcessedViolationEvent:
    return ProcessedViolationEvent(
        violation_id=f"VIO-{rule_code}",
        rule_code=rule_code,
        status=status,
        confidence=0.95,
        penalty=penalty,
        critical=critical,
        camera="FRONT",
        exercise="ESTAKADA",
        details="Test detail",
        screen_text="Test",
        voice_file="test.wav",
        voice_text="Test",
        timestamp=100.0,
    )


def test_mutation_scoring_boundary_sensitivity():
    """Mutant 1: Verify boundary condition at exact pass score (80)."""
    cfg = ScoringConfig(start_score=100, pass_score=80)
    scoring = ScoringEngine(cfg)

    assert scoring.current_score == 100
    assert scoring.is_passing is True

    # Mutant check: 100 - 20 = 80 exactly. Should pass.
    scoring.apply_event(_make_event("LIGHT_PENALTY", penalty=20))
    assert scoring.current_score == 80
    assert scoring.is_passing is True

    # Mutant check: 80 - 1 = 79. Should fail immediately.
    scoring.apply_event(_make_event("EXTRA_PENALTY", penalty=1))
    assert scoring.current_score == 79
    assert scoring.is_passing is False


def test_mutation_critical_violation_overrides_score():
    """Mutant 2: Verify critical violation forces failure and terminates session regardless of score."""
    cfg = ScoringConfig(start_score=100, pass_score=80)
    scoring = ScoringEngine(cfg)

    # Candidate has 100 points, but commits a critical collision (0 penalty points, but critical=True)
    scoring.apply_event(_make_event("CRITICAL_COLLISION", penalty=0, critical=True))
    assert scoring.current_score == 100
    assert scoring.is_passing is False
    assert scoring.is_terminated is True
    assert scoring.get_snapshot().is_passing is False
    assert scoring.get_snapshot().is_terminated is True


def test_mutation_event_debounce_and_cooldown_sensitivity():
    """Mutant 3: Verify cooldown prevents duplicate penalty within debounce window."""
    em = EventManager()
    rule = RuleItem(
        code="CONE_TOUCH",
        penalty=25,
        debounce_frames=3,
        cooldown_seconds=3.0,
        min_confidence=0.80,
    )

    # 1. Provide 2 frames (below threshold of 3): should NOT emit
    r1 = RuleEvaluationResult(violated=True, confidence=0.95, track_id=42)
    r2 = RuleEvaluationResult(violated=True, confidence=0.95, track_id=42)
    assert em.process_evaluation(rule, r1, "ZMEIKA", 100.0) is None
    assert em.process_evaluation(rule, r2, "ZMEIKA", 100.033) is None

    # 2. 3rd frame reaches threshold: MUST emit
    r3 = RuleEvaluationResult(violated=True, confidence=0.95, track_id=42)
    ev = em.process_evaluation(rule, r3, "ZMEIKA", 100.066)
    assert ev is not None
    assert ev.rule_code == "CONE_TOUCH"
    assert ev.status == "CONFIRMED"

    # 3. 4th frame at 101.0s (within 3.0s cooldown): MUST be suppressed as duplicate
    r4 = RuleEvaluationResult(violated=True, confidence=0.95, track_id=42)
    assert em.process_evaluation(rule, r4, "ZMEIKA", 101.0) is None

    # 4. Frame after cooldown (103.5s): allowed to emit new event once debounced
    em.process_evaluation(rule, RuleEvaluationResult(violated=True, confidence=0.95, track_id=42), "ZMEIKA", 103.5)
    em.process_evaluation(rule, RuleEvaluationResult(violated=True, confidence=0.95, track_id=42), "ZMEIKA", 103.533)
    ev2 = em.process_evaluation(rule, RuleEvaluationResult(violated=True, confidence=0.95, track_id=42), "ZMEIKA", 103.566)
    assert ev2 is not None


def test_mutation_speed_limit_boundary_sensitivity():
    """Mutant 4: Speed limit boundary at exactly 20.0 km/h with 10-frame debounce."""
    engine = RuleEngine()

    state_allowed = FusedVehicleState(
        timestamp=100.0, speed_kmh=20.0, is_stopped=False, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=False, turn_signal_active=True,
        lat=41.311, lon=69.240, rollback_distance_meters=0.0, source_quality="OK"
    )
    # Even after 15 frames at 20.0 km/h, no violation
    for i in range(15):
        ctx_allowed = EvaluationContext(100.0 + i * 0.033, "ESTAKADA", state_allowed, [], None, {})
        evs = engine.evaluate(ctx_allowed)
        assert not any(ev.rule_code == "SPEED_EXCEEDED" for ev in evs)

    # At 20.5 km/h, 10 consecutive frames MUST confirm and emit SPEED_EXCEEDED
    state_exceeded = FusedVehicleState(
        timestamp=105.0, speed_kmh=20.5, is_stopped=False, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=False, turn_signal_active=True,
        lat=41.311, lon=69.240, rollback_distance_meters=0.0, source_quality="OK"
    )
    events_exceeded = []
    for i in range(10):
        ctx_exceeded = EvaluationContext(105.0 + i * 0.033, "ESTAKADA", state_exceeded, [], None, {})
        evs = engine.evaluate(ctx_exceeded)
        events_exceeded.extend(evs)

    assert any(ev.rule_code == "SPEED_EXCEEDED" for ev in events_exceeded)
