"""Replay test suite comparing simulated sensor/camera streams against annotated Ground Truth.

Computes and asserts Precision and Recall per rule to prevent regressions.
"""

from dataclasses import dataclass

from driving_eval.ai.detector_base import BoundingBox, Detection
from driving_eval.hardware.sensor_fusion import FusedVehicleState
from driving_eval.rules.base_rule import EvaluationContext
from driving_eval.rules.engine import RuleEngine


@dataclass
class GroundTruthScenario:
    scenario_id: str
    description: str
    exercise: str
    vehicle_states: list[FusedVehicleState]
    frame_detections: list[list[Detection]]
    expected_violations: list[str]  # rule_codes that MUST be confirmed


def test_replay_ground_truth_precision_and_recall():
    # Ground Truth Test Scenarios
    scenarios: list[GroundTruthScenario] = [
        # Scenario 1: Clean driving, zero violations expected
        GroundTruthScenario(
            scenario_id="SCENARIO_CLEAN_DRIVE",
            description="Talaba xatosiz va to'g'ri tezlikda haydaydi",
            exercise="START",
            vehicle_states=[
                FusedVehicleState(10.0 + i * 0.1, 15.0, False, 0.0, True, False, True, 41.31, 69.24, 0.0, "OK")
                for i in range(20)
            ],
            frame_detections=[[] for _ in range(20)],
            expected_violations=[],
        ),
        # Scenario 2: Cone touch on Zmeika
        GroundTruthScenario(
            scenario_id="SCENARIO_CONE_TOUCH",
            description="Talaba Zmeykada konusga 10 kadr tegib turadi",
            exercise="ZMEIKA",
            vehicle_states=[
                FusedVehicleState(20.0 + i * 0.05, 8.0, False, 0.0, True, False, False, 41.31, 69.24, 0.0, "OK")
                for i in range(15)
            ],
            frame_detections=[
                [
                    Detection(
                        label="cone",
                        confidence=0.92,
                        bbox=BoundingBox(500, 620, 560, 690),
                        camera="FRONT",
                        timestamp=20.0 + i * 0.05,
                        track_id=1,
                    )
                ]
                for i in range(15)
            ],
            expected_violations=["CONE_TOUCH"],
        ),
        # Scenario 3: Seatbelt unfastened
        GroundTruthScenario(
            scenario_id="SCENARIO_SEATBELT_OFF",
            description="Kamarni taqmasdan harakatlanish",
            exercise="START",
            vehicle_states=[
                FusedVehicleState(30.0 + i * 0.05, 12.0, False, 0.0, False, False, False, 41.31, 69.24, 0.0, "OK")
                for i in range(20)
            ],
            frame_detections=[[] for _ in range(20)],
            expected_violations=["SEATBELT_UNFASTENED"],
        ),
        # Scenario 4: Stop line violation
        GroundTruthScenario(
            scenario_id="SCENARIO_STOP_LINE_BREACH",
            description="Stop chizig'ini bosib o'tish",
            exercise="STOP",
            vehicle_states=[
                FusedVehicleState(40.0 + i * 0.05, 5.0, False, 0.0, True, False, False, 41.31, 69.24, 0.0, "OK")
                for i in range(15)
            ],
            frame_detections=[
                [
                    Detection(
                        label="stop_line",
                        confidence=0.90,
                        bbox=BoundingBox(200, 650, 1080, 695),
                        camera="FRONT",
                        timestamp=40.0 + i * 0.05,
                        track_id=5,
                    )
                ]
                for i in range(15)
            ],
            expected_violations=["STOP_LINE_VIOLATION"],
        ),
    ]

    # Metrics Accumulator
    metrics = {
        "CONE_TOUCH": {"TP": 0, "FP": 0, "FN": 0},
        "SEATBELT_UNFASTENED": {"TP": 0, "FP": 0, "FN": 0},
        "STOP_LINE_VIOLATION": {"TP": 0, "FP": 0, "FN": 0},
    }

    for sc in scenarios:
        # Re-initialize engine per scenario to reset states
        sc_engine = RuleEngine()
        detected_violations = set()

        for step in range(len(sc.vehicle_states)):
            st = sc.vehicle_states[step]
            dets = sc.frame_detections[step]
            ctx = EvaluationContext(
                timestamp=st.timestamp,
                current_exercise=sc.exercise,
                vehicle_state=st,
                detections=dets,
                frame_bundle=None,
                calibrations={},
            )
            emitted = sc_engine.evaluate(ctx)
            for ev in emitted:
                if ev.status == "CONFIRMED":
                    detected_violations.add(ev.rule_code)

        expected_set = set(sc.expected_violations)
        all_rules = set(metrics.keys())

        for r_code in all_rules:
            is_expected = r_code in expected_set
            is_detected = r_code in detected_violations

            if is_expected and is_detected:
                metrics[r_code]["TP"] += 1
            elif not is_expected and is_detected:
                metrics[r_code]["FP"] += 1
            elif is_expected and not is_detected:
                metrics[r_code]["FN"] += 1

    # Print Precision / Recall Table
    print("\n\n" + "=" * 65)
    print(f"{'Qoida Kodi':<25} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 65)

    for r_code, counts in metrics.items():
        tp = counts["TP"]
        fp = counts["FP"]
        fn = counts["FN"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 1.0

        print(f"{r_code:<25} | {precision:<10.2f} | {recall:<10.2f} | {f1:<10.2f}")

        # Strict Quality Gate: Precision and Recall must be 100% on ground truth benchmarks!
        assert precision >= 0.99, f"Precision failed for {r_code}: {precision}"
        assert recall >= 0.99, f"Recall failed for {r_code}: {recall}"

    print("=" * 65)
