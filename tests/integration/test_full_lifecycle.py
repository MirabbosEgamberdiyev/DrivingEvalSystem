"""Full end-to-end integration test of the entire driving evaluation lifecycle."""


from driving_eval.ai.detector_base import BoundingBox, Detection
from driving_eval.ai.exercise_detector import ExerciseDetector
from driving_eval.ai.mock_detector import MockDetector
from driving_eval.audio.audio_service import AudioService
from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.state_machine import ExamState, ExamStateMachine
from driving_eval.db.repository import DatabaseRepository
from driving_eval.evidence.recorder import EvidenceRecorder
from driving_eval.hardware.camera_service import MultiCameraService
from driving_eval.hardware.precheck import PrecheckService
from driving_eval.hardware.sensor_fusion import FusedVehicleState
from driving_eval.reporting.pdf_report import generate_pdf_report
from driving_eval.rules.base_rule import EvaluationContext
from driving_eval.rules.engine import RuleEngine
from driving_eval.rules.scoring import ScoringEngine


def test_full_system_lifecycle_end_to_end(tmp_path):
    cfg = SystemConfig.load_from_yaml("config/config.yaml")
    cfg.storage.db_path = str(tmp_path / "lifecycle.db")
    cfg.storage.base_dir = str(tmp_path / "data")
    cfg.storage.evidence_dir = str(tmp_path / "data" / "evidence")
    cfg.storage.min_free_disk_gb = 1.0

    repo = DatabaseRepository(cfg.storage.db_path)
    repo.sync_rules("config/rules.yaml")

    cam_service = MultiCameraService(cfg.cameras, simulation_mode=True)
    cam_service.start_all()
    import time
    time.sleep(0.3)
    detector = MockDetector(healthy=True)
    audio = AudioService(cfg.audio, simulate_playback=True)
    audio.start()
    recorder = EvidenceRecorder(cfg.storage.evidence_dir, repo, buffer_duration_seconds=2.0, fps=10)
    rule_engine = RuleEngine()
    scoring = ScoringEngine(cfg.scoring)
    exercise_detector = ExerciseDetector(cfg.exercises)

    try:
        # 1. BOOT & PRECHECK
        sm = ExamStateMachine(repository=repo)
        sm.transition_to(ExamState.BOOT, "Boot")
        sm.transition_to(ExamState.READY, "Ready")

        precheck = PrecheckService(cfg, cam_service, detector, repo, {})
        report = precheck.run_all_checks()
        assert report.passed is True

        sm.transition_to(ExamState.PRECHECK, "Precheck")
        sm.transition_to(ExamState.CAMERA_CHECK, "Cameras OK")
        sm.transition_to(ExamState.SYSTEM_CHECK, "System OK")
        sm.transition_to(ExamState.TEST_READY, "Test Ready")

        # 2. START ACTIVE TEST
        stu_id = repo.register_or_get_student("PASS001", "Jasur", "Olimov")
        veh_id = repo.register_vehicle("CAR-UZ-01", "VIN123", "01A777AA", "Cobalt", 2024)
        session_id = "SESS-E2E-001"
        repo.create_session(session_id, stu_id, veh_id, 100, "1.0.0", "1.0.0")

        sm.transition_to(ExamState.TEST_ACTIVE, "Test active started")
        assert sm.is_scoring_active() is True

        # 3. Simulate Vehicle Driving & Violations
        # In ZMEIKA: Cone touch (confirmed, -25)
        exercise_detector.force_set_exercise("ZMEIKA")
        t = 100.0
        cone_det = Detection("cone", 0.92, BoundingBox(500, 600, 550, 690), "FRONT", t, track_id=7)
        state_zmeika = FusedVehicleState(t, 10.0, False, 0.0, True, False, False, 41.31, 69.24, 0.0, "OK")

        # 6 frames of cone touch to trigger debounce
        for f in range(6):
            ctx = EvaluationContext(t + f * 0.05, "ZMEIKA", state_zmeika, [cone_det], None, {})
            events = rule_engine.evaluate(ctx)
            for ev in events:
                scoring.apply_event(ev)
                repo.record_violation(ev.violation_id, session_id, ev.status, ev.confidence, ev.camera, ev.exercise, ev.rule_code, ev.details)
                repo.record_penalty(ev.violation_id, session_id, ev.penalty)
                recorder.record_evidence_package(session_id, ev)
                audio.enqueue_alert(ev.voice_file, ev.voice_text, ev.critical, ev.rule_code)

        assert scoring.current_score == 75
        assert scoring.total_penalty == 25

        # In STOP: Suspect line detection (confidence 0.60 < 0.82) -> SUSPECT, 0 penalty!
        exercise_detector.force_set_exercise("STOP")
        line_det = Detection("stop_line", 0.60, BoundingBox(200, 675, 1000, 695), "FRONT", t + 10.0, track_id=9)
        state_stop = FusedVehicleState(t + 10.0, 5.0, False, 0.0, True, False, False, 41.31, 69.24, 0.0, "OK")

        for f in range(9):
            ctx_sus = EvaluationContext(t + 10.0 + f * 0.05, "STOP", state_stop, [line_det], None, {})
            events = rule_engine.evaluate(ctx_sus)
            for ev in events:
                scoring.apply_event(ev)
                repo.record_violation(ev.violation_id, session_id, ev.status, ev.confidence, ev.camera, ev.exercise, ev.rule_code, ev.details)

        # Score remains 75 (SUSPECT deducted 0 points!)
        assert scoring.current_score == 75
        assert len(scoring.suspect_events) == 1

        # 4. FINISH ZONE ARRIVAL & STOPPING
        exercise_detector.force_set_exercise("FINISH")
        finish_zone = exercise_detector._zones["FINISH"]
        sm.transition_to(ExamState.FINISH_DETECTED, "Finish zonasiga kirdi")

        state_stopped_finish = FusedVehicleState(t + 22.0, 0.0, True, 0.0, True, True, False, finish_zone.lat, finish_zone.lon, 0.0, "OK")
        assert exercise_detector.can_finalize_test(state_stopped_finish) is True

        sm.transition_to(ExamState.VEHICLE_STOPPED, "Mashina to'xtadi")
        sm.transition_to(ExamState.FINALIZING, "Finalizing")

        # 5. RESULT & COMPLETED
        root_hash = repo.finalize_test_result(
            session_id=session_id,
            final_score=scoring.current_score,
            result="FAIL",  # 75 < 80
            critical_count=0,
            suspect_count=len(scoring.suspect_events),
        )
        assert len(root_hash) == 64
        assert repo.verify_session_hash_integrity(session_id) is True

        sm.transition_to(ExamState.RESULT_READY, "Result ready")
        sm.transition_to(ExamState.COMPLETED, "Completed")
        assert sm.current_state == ExamState.COMPLETED

        # 6. PDF REPORT VERIFICATION
        sess = repo.get_session(session_id)
        violations = repo.get_violations_for_session(session_id)
        out_pdf = tmp_path / "final_report.pdf"
        generate_pdf_report(
            out_pdf,
            sess,
            {"first_name": "Jasur", "last_name": "Olimov", "passport_id": "PASS001"},
            {"model": "Cobalt", "plate_number": "01A777AA"},
            violations,
            root_hash,
        )
        assert out_pdf.exists()
        assert out_pdf.stat().st_size > 1000

    finally:
        cam_service.stop_all()
        audio.stop()
