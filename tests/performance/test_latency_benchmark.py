"""Latency benchmark: Measures frame capture-to-alert processing latency.

Target: < 200 ms for complete pipeline processing.
"""

import time

import numpy as np

from driving_eval.ai.detector_base import BoundingBox, Detection
from driving_eval.ai.exercise_detector import ExerciseDetector
from driving_eval.ai.mock_detector import MockDetector
from driving_eval.ai.tracker import SimpleByteTracker
from driving_eval.core.config_schema import SystemConfig
from driving_eval.hardware.sensor_fusion import FusedVehicleState
from driving_eval.rules.base_rule import EvaluationContext
from driving_eval.rules.engine import RuleEngine
from driving_eval.rules.scoring import ScoringEngine


def test_frame_to_alert_latency_benchmark():
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    detector = MockDetector(healthy=True)
    tracker = SimpleByteTracker()
    rule_engine = RuleEngine()
    scoring = ScoringEngine(cfg.scoring)
    exercise_detector = ExerciseDetector(cfg.exercises)

    # 100 test iterations
    latencies_ms: list[float] = []
    synthetic_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    state = FusedVehicleState(
        timestamp=100.0, speed_kmh=12.0, is_stopped=False, pitch_deg=0.0,
        seatbelt_fastened=True, handbrake_active=False, turn_signal_active=True,
        lat=41.311, lon=69.240, rollback_distance_meters=0.0, source_quality="OK"
    )

    for i in range(100):
        t0 = time.perf_counter()

        # 1. Detection
        ts = 100.0 + i * 0.033
        # Inject cone detection every 10 frames
        if i % 10 == 0:
            detector.schedule_detection(
                Detection("cone", 0.90, BoundingBox(500, 600, 560, 690), "FRONT", ts)
            )
        dets = detector.detect(synthetic_frame, "FRONT", ts)

        # 2. Tracking
        tracked = tracker.update(dets, ts)

        # 3. Exercise & Rules
        exercise, _, _ = exercise_detector.update_location(state)
        ctx = EvaluationContext(
            timestamp=ts,
            current_exercise=exercise,
            vehicle_state=state,
            detections=tracked,
            frame_bundle=None,
            calibrations={},
        )
        new_events = rule_engine.evaluate(ctx)

        # 4. Scoring
        for ev in new_events:
            scoring.apply_event(ev)

        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    p50 = float(np.percentile(latencies_ms, 50))
    p95 = float(np.percentile(latencies_ms, 95))
    max_lat = max(latencies_ms)

    print("\n--- LATENCY BENCHMARK NATIJALARI ---")
    print(f"P50 Latency: {p50:.2f} ms")
    print(f"P95 Latency: {p95:.2f} ms (Maqsad: < 200 ms)")
    print(f"Max Latency: {max_lat:.2f} ms")

    assert p95 < 200.0, f"P95 latency exceeded threshold: {p95:.2f} ms >= 200 ms"
