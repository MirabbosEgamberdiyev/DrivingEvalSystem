"""Replay test suite comparing simulated sensor and camera streams against Ground Truth annotations.

Evaluates the complete pipeline:
SimpleByteTracker -> ExerciseDetector -> RuleEngine -> EventManager -> ScoringEngine.
Computes and asserts 100% Precision and Recall per rule to prevent regressions.
"""

import tempfile
from pathlib import Path

from driving_eval.ai.detector_base import BoundingBox, Detection
from driving_eval.hardware.sensor_fusion import FusedVehicleState
from driving_eval.replay.session_replay import (
    GroundTruthViolation,
    ReplayFrame,
    ReplayScenario,
    SessionReplayer,
)


def _make_vehicle_state(
    timestamp: float,
    speed_kmh: float = 12.0,
    seatbelt_fastened: bool = True,
    turn_signal_active: bool = True,
    rollback_distance: float = 0.0,
) -> FusedVehicleState:
    return FusedVehicleState(
        timestamp=timestamp,
        speed_kmh=speed_kmh,
        is_stopped=(speed_kmh < 0.5),
        pitch_deg=0.0,
        seatbelt_fastened=seatbelt_fastened,
        handbrake_active=False,
        turn_signal_active=turn_signal_active,
        lat=41.311081,
        lon=69.240562,
        rollback_distance_meters=rollback_distance,
        source_quality="OK",
    )


def test_replay_ground_truth_full_suite():
    replayer = SessionReplayer()

    # 1. Clean Drive Scenario (PASS, 100 score, 0 violations)
    clean_scenario = ReplayScenario(
        scenario_id="SCENARIO_01_CLEAN",
        name="A'lo haydash (Xatosiz)",
        description="Barcha mashqlar xatosiz bajarilgan ideal haydash",
        frames=[
            ReplayFrame(
                timestamp=10.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(10.0 + i * 0.1, speed_kmh=12.0),
                exercise="START",
                detections=[],
            )
            for i in range(25)
        ],
        expected_violations=[],
    )
    report_clean = replayer.replay(clean_scenario)
    assert report_clean.final_score == 100
    assert report_clean.is_passing is True
    assert report_clean.is_terminated is False
    assert len(report_clean.confirmed_events) == 0
    passed_gates, failures = report_clean.verify_quality_gates(min_precision=1.0, min_recall=1.0)
    assert passed_gates, f"Clean scenario quality gate failed: {failures}"

    # 2. Cone Touch on Zmeika (CONE_TOUCH, debounce: 5 frames)
    cone_scenario = ReplayScenario(
        scenario_id="SCENARIO_02_CONE_TOUCH",
        name="Zmeykada konusga tegish",
        description="Zmeyka mashqida konusga yaqinlashib tegish",
        frames=[
            ReplayFrame(
                timestamp=20.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(20.0 + i * 0.1, speed_kmh=8.0),
                exercise="ZMEIKA",
                detections=[
                    Detection("cone", 0.92, BoundingBox(500, 620, 560, 690), "FRONT", 20.0 + i * 0.1, track_id=1)
                ],
            )
            for i in range(15)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="CONE_TOUCH", timestamp_start=20.0, timestamp_end=21.5, exercise="ZMEIKA")
        ],
    )
    report_cone = replayer.replay(cone_scenario)
    assert report_cone.final_score == 75  # 100 - 25
    assert len(report_cone.confirmed_events) == 1
    assert report_cone.confirmed_events[0].rule_code == "CONE_TOUCH"
    assert report_cone.rule_metrics["CONE_TOUCH"].true_positives == 1
    assert report_cone.rule_metrics["CONE_TOUCH"].false_positives == 0
    assert report_cone.rule_metrics["CONE_TOUCH"].precision == 1.0
    assert report_cone.rule_metrics["CONE_TOUCH"].recall == 1.0

    # 3. Seatbelt Unfastened (SEATBELT_UNFASTENED, debounce: 15 frames)
    seatbelt_scenario = ReplayScenario(
        scenario_id="SCENARIO_03_SEATBELT",
        name="Kamarni taqmasdan harakatlanish",
        description="Boshlang'ich harakatda kamar taqilmagan",
        frames=[
            ReplayFrame(
                timestamp=30.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(30.0 + i * 0.1, speed_kmh=12.0, seatbelt_fastened=False),
                exercise="START",
                detections=[],
            )
            for i in range(20)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="SEATBELT_UNFASTENED", timestamp_start=30.0, timestamp_end=32.0, exercise="START")
        ],
    )
    report_seatbelt = replayer.replay(seatbelt_scenario)
    assert report_seatbelt.final_score == 90  # 100 - 10
    assert report_seatbelt.rule_metrics["SEATBELT_UNFASTENED"].precision == 1.0
    assert report_seatbelt.rule_metrics["SEATBELT_UNFASTENED"].recall == 1.0

    # 4. Stop Line Overrun (STOP_LINE_VIOLATION, debounce: 8 frames)
    stop_scenario = ReplayScenario(
        scenario_id="SCENARIO_04_STOP_LINE",
        name="Stop chizig'ini bosish",
        description="Stop mashqida chiziqdan o'tib ketish",
        frames=[
            ReplayFrame(
                timestamp=40.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(40.0 + i * 0.1, speed_kmh=4.0),
                exercise="STOP",
                detections=[
                    Detection("stop_line", 0.90, BoundingBox(200, 650, 1080, 695), "FRONT", 40.0 + i * 0.1, track_id=2)
                ],
            )
            for i in range(15)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="STOP_LINE_VIOLATION", timestamp_start=40.0, timestamp_end=41.5, exercise="STOP")
        ],
    )
    report_stop = replayer.replay(stop_scenario)
    assert report_stop.final_score == 80  # 100 - 20
    assert report_stop.rule_metrics["STOP_LINE_VIOLATION"].precision == 1.0
    assert report_stop.rule_metrics["STOP_LINE_VIOLATION"].recall == 1.0

    # 5. Hill Rollback on Estakada (HILL_ROLLBACK, debounce: 10 frames)
    estakada_scenario = ReplayScenario(
        scenario_id="SCENARIO_05_HILL_ROLLBACK",
        name="Estakadada orqaga sirg'alish",
        description="Estakada mashqida 0.35 metr orqaga sirg'alish",
        frames=[
            ReplayFrame(
                timestamp=50.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(50.0 + i * 0.1, speed_kmh=0.0, rollback_distance=0.35),
                exercise="ESTAKADA",
                detections=[],
            )
            for i in range(15)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="HILL_ROLLBACK", timestamp_start=50.0, timestamp_end=51.5, exercise="ESTAKADA")
        ],
    )
    report_estakada = replayer.replay(estakada_scenario)
    assert report_estakada.final_score == 70  # 100 - 30
    assert report_estakada.rule_metrics["HILL_ROLLBACK"].precision == 1.0
    assert report_estakada.rule_metrics["HILL_ROLLBACK"].recall == 1.0

    # 6. Speed Exceeded on Autodrome (SPEED_EXCEEDED, debounce: 10 frames)
    speed_scenario = ReplayScenario(
        scenario_id="SCENARIO_06_SPEED_EXCEEDED",
        name="Tezlikni oshirish",
        description="Avtodromda 32 km/h tezlikda harakatlanish",
        frames=[
            ReplayFrame(
                timestamp=60.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(60.0 + i * 0.1, speed_kmh=32.0),
                exercise="ZMEIKA",
                detections=[],
            )
            for i in range(15)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="SPEED_EXCEEDED", timestamp_start=60.0, timestamp_end=61.5, exercise="ZMEIKA")
        ],
    )
    report_speed = replayer.replay(speed_scenario)
    assert report_speed.final_score == 85  # 100 - 15
    assert report_speed.rule_metrics["SPEED_EXCEEDED"].precision == 1.0
    assert report_speed.rule_metrics["SPEED_EXCEEDED"].recall == 1.0

    # 7. Turn Indicator Missed (INDICATOR_MISSED, debounce: 12 frames)
    indicator_scenario = ReplayScenario(
        scenario_id="SCENARIO_07_INDICATOR_MISSED",
        name="Burilish chirog'ini yoqmaslik",
        description="90 gradus burilishda chiroq yoqilmagan",
        frames=[
            ReplayFrame(
                timestamp=70.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(70.0 + i * 0.1, speed_kmh=12.0, turn_signal_active=False),
                exercise="TURN_90",
                detections=[],
            )
            for i in range(18)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="INDICATOR_MISSED", timestamp_start=70.0, timestamp_end=71.8, exercise="TURN_90")
        ],
    )
    report_indicator = replayer.replay(indicator_scenario)
    assert report_indicator.final_score == 90  # 100 - 10
    assert report_indicator.rule_metrics["INDICATOR_MISSED"].precision == 1.0
    assert report_indicator.rule_metrics["INDICATOR_MISSED"].recall == 1.0

    # 8. Parking Out of Bounds (PARKING_OUT_OF_BOUNDS, debounce: 10 frames)
    parking_scenario = ReplayScenario(
        scenario_id="SCENARIO_08_PARKING_BOUNDS",
        name="Parkovka chizig'idan chiqish",
        description="Parallel parkovkada yon g'ildirak chiziqni bosishi",
        frames=[
            ReplayFrame(
                timestamp=80.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(80.0 + i * 0.1, speed_kmh=2.0),
                exercise="PARALLEL_PARKING",
                detections=[
                    Detection("parking_line", 0.91, BoundingBox(100, 660, 450, 710), "RIGHT", 80.0 + i * 0.1, track_id=4)
                ],
            )
            for i in range(16)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="PARKING_OUT_OF_BOUNDS", timestamp_start=80.0, timestamp_end=81.6, exercise="PARALLEL_PARKING")
        ],
    )
    report_parking = replayer.replay(parking_scenario)
    assert report_parking.final_score == 75  # 100 - 25
    assert report_parking.rule_metrics["PARKING_OUT_OF_BOUNDS"].precision == 1.0
    assert report_parking.rule_metrics["PARKING_OUT_OF_BOUNDS"].recall == 1.0

    # 9. Critical Collision (CRITICAL_COLLISION, debounce: 3 frames)
    collision_scenario = ReplayScenario(
        scenario_id="SCENARIO_09_CRITICAL_COLLISION",
        name="To'siqqa to'qnashuv",
        description="To'siqqa urilish (Imtihon darhol to'xtatiladi)",
        frames=[
            ReplayFrame(
                timestamp=90.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(90.0 + i * 0.1, speed_kmh=10.0),
                exercise="START",
                detections=[
                    Detection("barrier", 0.95, BoundingBox(300, 685, 800, 715), "FRONT", 90.0 + i * 0.1, track_id=7)
                ],
            )
            for i in range(8)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="CRITICAL_COLLISION", timestamp_start=90.0, timestamp_end=90.8, exercise="START", critical=True)
        ],
    )
    report_coll = replayer.replay(collision_scenario)
    assert report_coll.is_terminated is True
    assert report_coll.is_passing is False
    assert report_coll.rule_metrics["CRITICAL_COLLISION"].precision == 1.0
    assert report_coll.rule_metrics["CRITICAL_COLLISION"].recall == 1.0

    # 10. Exercise Sequence Broken (EXERCISE_SEQUENCE_BROKEN, debounce: 5 frames)
    seq_scenario = ReplayScenario(
        scenario_id="SCENARIO_10_SEQ_BROKEN",
        name="Mashqlar ketma-ketligi buzilishi",
        description="Zmeykani tashlab to'g'ridan-to'g'ri Stoppa o'tish",
        frames=[
            ReplayFrame(
                timestamp=100.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(100.0 + i * 0.1, speed_kmh=15.0),
                exercise="STOP",
                detections=[
                    Detection("SEQUENCE_BROKEN", 0.95, BoundingBox(0, 0, 10, 10), "FRONT", 100.0 + i * 0.1, metadata={"message": "ZMEIKA tashlab ketildi"})
                ],
            )
            for i in range(10)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="EXERCISE_SEQUENCE_BROKEN", timestamp_start=100.0, timestamp_end=101.0, exercise="STOP", critical=True)
        ],
    )
    report_seq = replayer.replay(seq_scenario)
    assert report_seq.is_terminated is True
    assert report_seq.rule_metrics["EXERCISE_SEQUENCE_BROKEN"].precision == 1.0
    assert report_seq.rule_metrics["EXERCISE_SEQUENCE_BROKEN"].recall == 1.0

    # 11. Suspect Isolation (Low Confidence < 0.80): 0 penalty, score remains 100!
    suspect_scenario = ReplayScenario(
        scenario_id="SCENARIO_11_SUSPECT",
        name="Past ishonchli konus teginishi (SUSPECT)",
        description="Konus aniqligi 0.65 (<0.80). Jarima yozilmaydi, faqat inspektor ro'yxatiga tushadi",
        frames=[
            ReplayFrame(
                timestamp=110.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(110.0 + i * 0.1, speed_kmh=8.0),
                exercise="ZMEIKA",
                detections=[
                    Detection("cone", 0.65, BoundingBox(500, 620, 560, 690), "FRONT", 110.0 + i * 0.1, track_id=9)
                ],
            )
            for i in range(12)
        ],
        expected_violations=[],  # Zero confirmed violations expected!
    )
    report_suspect = replayer.replay(suspect_scenario)
    assert report_suspect.final_score == 100  # Strictly 0 penalty deduction!
    assert report_suspect.is_passing is True
    assert len(report_suspect.confirmed_events) == 0
    assert len(report_suspect.suspect_events) == 1
    assert report_suspect.rule_metrics["CONE_TOUCH"].suspect_count == 1
    assert report_suspect.rule_metrics["CONE_TOUCH"].false_positives == 0  # No false alarm!

    # 12. Deduplication & Cooldown Guarantee: Continuous 25 frames produce EXACTLY 1 event!
    dedup_scenario = ReplayScenario(
        scenario_id="SCENARIO_12_DEDUP",
        name="25 kadr uzluksiz konusga tegish",
        description="25 kadr davomida konusga tegganda aynan 1 ta hodisa va 1 ta jarima bo'lishini tekshirish",
        frames=[
            ReplayFrame(
                timestamp=120.0 + i * 0.1,
                vehicle_state=_make_vehicle_state(120.0 + i * 0.1, speed_kmh=6.0),
                exercise="ZMEIKA",
                detections=[
                    Detection("cone", 0.90, BoundingBox(500, 620, 560, 690), "FRONT", 120.0 + i * 0.1, track_id=12)
                ],
            )
            for i in range(25)
        ],
        expected_violations=[
            GroundTruthViolation(rule_code="CONE_TOUCH", timestamp_start=120.0, timestamp_end=122.5, exercise="ZMEIKA")
        ],
    )
    report_dedup = replayer.replay(dedup_scenario)
    assert len(report_dedup.confirmed_events) == 1  # Guaranteed exactly 1 event!
    assert report_dedup.final_score == 75  # Exactly 25 penalty points deducted!

    # 13. Verify Report Exports (JSON, CSV, Markdown)
    with tempfile.TemporaryDirectory() as tmp_dir:
        json_path = Path(tmp_dir) / "report.json"
        csv_path = Path(tmp_dir) / "report.csv"

        report_dedup.export_json(json_path)
        report_dedup.export_csv(csv_path)

        assert json_path.exists() and json_path.stat().st_size > 0
        assert csv_path.exists() and csv_path.stat().st_size > 0

        md = report_dedup.summary_markdown()
        assert "Replay Benchmark Natijasi" in md
        assert "CONE_TOUCH" in md
        assert "FAIL ❌" in md

        md_clean = report_clean.summary_markdown()
        assert "PASS ✅" in md_clean
