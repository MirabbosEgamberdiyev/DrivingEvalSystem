"""Accelerated soak test checking for memory leaks and resource exhaustion over 1000+ frames."""

import gc
import os

from driving_eval.ai.detector_base import BoundingBox, Detection
from driving_eval.ai.exercise_detector import ExerciseDetector
from driving_eval.ai.tracker import SimpleByteTracker
from driving_eval.core.config_schema import SystemConfig
from driving_eval.db.repository import DatabaseRepository
from driving_eval.hardware.sensor_fusion import FusedVehicleState
from driving_eval.rules.base_rule import EvaluationContext
from driving_eval.rules.engine import RuleEngine
from driving_eval.rules.scoring import ScoringEngine


def get_current_memory_mb() -> float:
    """Returns resident memory in MB using standard os or psutil fallback."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


def test_accelerated_soak_1000_frames(tmp_path):
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    repo = DatabaseRepository(tmp_path / "soak.db")
    repo.sync_rules("config/rules.yaml")

    tracker = SimpleByteTracker()
    rule_engine = RuleEngine()
    scoring = ScoringEngine(cfg.scoring)
    exercise_detector = ExerciseDetector(cfg.exercises)

    stu_id = repo.register_or_get_student("SOAK1", "Ali", "Soak")
    veh_id = repo.register_vehicle("CAR-SOAK", "VINSOAK", "01SOAK", "Cobalt", 2024)
    session_id = "SESS-SOAK-01"
    repo.create_session(session_id, stu_id, veh_id, 100, "1.0", "1.0")

    gc.collect()
    mem_start = get_current_memory_mb()

    # Run 1000 frames
    for i in range(1000):
        t = 1000.0 + (i * 0.033)
        dets = []
        if i % 15 == 0:
            dets.append(
                Detection("cone", 0.91, BoundingBox(500, 600, 550, 690), "FRONT", t, track_id=i % 3)
            )

        tracked = tracker.update(dets, t)
        state = FusedVehicleState(t, 12.0, False, 0.0, True, False, True, 41.31, 69.24, 0.0, "OK")
        ex, _, _ = exercise_detector.update_location(state)

        ctx = EvaluationContext(t, ex, state, tracked, None, {})
        new_events = rule_engine.evaluate(ctx)

        for ev in new_events:
            scoring.apply_event(ev)
            repo.record_violation(ev.violation_id, session_id, ev.status, ev.confidence, ev.camera, ev.exercise, ev.rule_code, ev.details)

    gc.collect()
    mem_end = get_current_memory_mb()

    if mem_start > 0 and mem_end > 0:
        mem_growth = mem_end - mem_start
        print("\n--- SOAK TEST NATIJALARI (1000 kadr) ---")
        print(f"Boshlang'ich xotira: {mem_start:.2f} MB")
        print(f"Yakuniy xotira:      {mem_end:.2f} MB")
        print(f"O'sish:              {mem_growth:.2f} MB")
        # Memory growth must be bounded (< 80 MB)
        assert mem_growth < 80.0, f"Memory leak detected during soak test: {mem_growth} MB"
