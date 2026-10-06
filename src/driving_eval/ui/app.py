"""Main PySide6 application window coordinating the lifecycle state machine and UI screens."""

import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from driving_eval.ai.detector_base import BaseDetector
from driving_eval.ai.exercise_detector import ExerciseDetector
from driving_eval.ai.tracker import SimpleByteTracker
from driving_eval.audio.audio_service import AudioService
from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.state_machine import ExamState, ExamStateMachine
from driving_eval.db.repository import DatabaseRepository
from driving_eval.evidence.recorder import EvidenceRecorder
from driving_eval.evidence.storage import StorageManager
from driving_eval.hardware.calibration import CalibrationService
from driving_eval.hardware.camera_service import MultiCameraService
from driving_eval.hardware.precheck import PrecheckService
from driving_eval.hardware.sensor_fusion import SensorFusionService
from driving_eval.reporting.pdf_report import generate_pdf_report
from driving_eval.rules.base_rule import EvaluationContext
from driving_eval.rules.engine import RuleEngine
from driving_eval.rules.scoring import ScoringEngine
from driving_eval.ui.kiosk import apply_kiosk_mode
from driving_eval.ui.screens.active_test_screen import ActiveTestScreen
from driving_eval.ui.screens.home_screen import HomeScreen
from driving_eval.ui.screens.precheck_screen import PrecheckScreen
from driving_eval.ui.screens.result_screen import ResultScreen
from driving_eval.ui.screens.settings_screen import SettingsScreen


class DrivingEvaluationApp(QMainWindow):
    """Top-level GUI window governing all exam stages according to the strict state machine."""

    def __init__(
        self,
        config: SystemConfig,
        repository: DatabaseRepository,
        camera_service: MultiCameraService,
        ai_detector: BaseDetector,
        audio_service: AudioService,
        evidence_recorder: EvidenceRecorder,
        storage_manager: StorageManager,
        kiosk_mode: bool = False,
    ):
        super().__init__()
        self.config = config
        self.repository = repository
        self.camera_service = camera_service
        self.ai_detector = ai_detector
        self.audio_service = audio_service
        self.evidence_recorder = evidence_recorder
        self.storage_manager = storage_manager

        self.setWindowTitle(config.ui.window_title)
        self.setStyleSheet("background-color: #1A202C;")
        self.resize(1280, 800)

        # Domain Services
        self.state_machine = ExamStateMachine(repository=self.repository)
        self.tracker = SimpleByteTracker()
        self.rule_engine = RuleEngine()
        self.scoring_engine = ScoringEngine(self.config.scoring)
        self.sensor_fusion = SensorFusionService(self.config.exercises.speed_stop_threshold_kmh)
        self.exercise_detector = ExerciseDetector(self.config.exercises)

        self.calibrations = {
            "FRONT": CalibrationService.load("config/calibration/front_camera.json"),
            "REAR": CalibrationService.load("config/calibration/rear_camera.json"),
            "LEFT": CalibrationService.load("config/calibration/left_camera.json"),
            "RIGHT": CalibrationService.load("config/calibration/right_camera.json"),
        }

        self.precheck_service = PrecheckService(
            config=self.config,
            camera_service=self.camera_service,
            ai_detector=self.ai_detector,
            repository=self.repository,
            calibrations=self.calibrations,
        )

        # Active Session Data
        self.current_session_id: str | None = None
        self.current_student_data: dict = {}
        self.session_start_monotonic: float = 0.0

        # UI Stack
        self._init_screens()

        # Engine Loop Timer (30 fps ~ 33 ms)
        self._loop_timer = QTimer(self)
        self._loop_timer.timeout.connect(self._engine_tick)

        # Transition to BOOT -> READY
        self.state_machine.transition_to(ExamState.BOOT, "Dastur ishga tushdi")
        self.state_machine.transition_to(ExamState.READY, "Asosiy ekran ochildi")

        if kiosk_mode:
            apply_kiosk_mode(self, enabled=True)

    def _init_screens(self) -> None:
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.home_screen = HomeScreen()
        self.home_screen.precheck_requested.connect(self._start_precheck)
        self.home_screen.open_settings_requested.connect(self._open_settings)

        self.precheck_screen = PrecheckScreen()
        self.precheck_screen.recheck_requested.connect(self._run_precheck)
        self.precheck_screen.proceed_to_test_ready.connect(self._proceed_to_test_ready)

        self.active_test_screen = ActiveTestScreen()
        self.active_test_screen.finish_requested.connect(self._finish_test)

        self.result_screen = ResultScreen()
        self.result_screen.pdf_export_requested.connect(self._export_pdf)
        self.result_screen.usb_export_requested.connect(self._export_usb)
        self.result_screen.next_candidate_requested.connect(self._reset_to_home)

        self.settings_screen = SettingsScreen(self.config.security.admin_pin_hash_sha256)
        self.settings_screen.close_requested.connect(lambda: self.stack.setCurrentWidget(self.home_screen))

        self.stack.addWidget(self.home_screen)          # Index 0
        self.stack.addWidget(self.precheck_screen)      # Index 1
        self.stack.addWidget(self.active_test_screen)   # Index 2
        self.stack.addWidget(self.result_screen)        # Index 3
        self.stack.addWidget(self.settings_screen)      # Index 4

        self.stack.setCurrentWidget(self.home_screen)

    def _open_settings(self) -> None:
        self.stack.setCurrentWidget(self.settings_screen)

    def _start_precheck(self, student_info: dict) -> None:
        self.current_student_data = student_info
        self.state_machine.transition_to(ExamState.PRECHECK, "Precheck so'raldi")
        self.stack.setCurrentWidget(self.precheck_screen)
        self._run_precheck()

    def _run_precheck(self) -> None:
        self.state_machine.transition_to(ExamState.CAMERA_CHECK, "Kameralar tekshirilmoqda")
        self.state_machine.transition_to(ExamState.SYSTEM_CHECK, "Tizim komponentlari")
        report = self.precheck_service.run_all_checks()
        self.precheck_screen.display_report(report)

    def _proceed_to_test_ready(self) -> None:
        self.state_machine.transition_to(ExamState.TEST_READY, "Barcha parametrlar tayyor")
        # Automatically launch test or let candidate click start
        self._start_active_test()

    def _start_active_test(self) -> None:
        # Register student and session
        stu_id = self.repository.register_or_get_student(
            self.current_student_data.get("passport_id", "AA1234567"),
            self.current_student_data.get("first_name", "Aziz"),
            self.current_student_data.get("last_name", "Rahimov"),
        )
        veh_id = self.repository.register_vehicle("CAR-UZ-01", "VIN123456", "01A777AA", "Cobalt", 2024)

        t_now = int(time.time())
        self.current_session_id = f"SESS-{t_now}"
        self.state_machine.set_session_id(self.current_session_id)

        self.repository.create_session(
            session_id=self.current_session_id,
            student_id=stu_id,
            vehicle_id=veh_id,
            start_score=self.config.scoring.start_score,
            rules_version=self.config.app.rules_version,
            app_version=self.config.app.version,
        )

        self.state_machine.transition_to(ExamState.TEST_ACTIVE, "Imtihon rasman boshlandi")
        self.session_start_monotonic = time.monotonic()
        self.stack.setCurrentWidget(self.active_test_screen)

        # Start live loop
        self._loop_timer.start(33)

    def _engine_tick(self) -> None:
        """Core real-time frame processing tick: Camera -> AI -> Tracker -> Rules -> Scoring."""
        if not self.state_machine.is_scoring_active():
            return

        now = time.monotonic()
        elapsed = int(now - self.session_start_monotonic)

        # 1. Fetch synchronized bundle
        bundle = self.camera_service.get_synchronized_bundle()
        if not bundle:
            return

        # Push to evidence ring buffer
        self.evidence_recorder.push_bundle(bundle)

        # 2. Perception & Tracking
        raw_detections = []
        for cam_name, cam_frame in bundle.frames.items():
            dets = self.ai_detector.detect(cam_frame.frame, cam_name, bundle.timestamp)
            raw_detections.extend(dets)

        tracked_detections = self.tracker.update(raw_detections, bundle.timestamp)

        # 3. Vehicle State & Exercise
        veh_state = self.sensor_fusion.get_fused_state(bundle.timestamp)
        exercise_name, seq_broken, seq_msg = self.exercise_detector.update_location(veh_state)

        # 4. Check Sequence Violation
        if seq_broken and self.state_machine.is_scoring_active():
            # Trigger critical sequence violation
            self._handle_critical_event("EXERCISE_SEQUENCE_BROKEN", seq_msg, bundle.timestamp)
            return

        # 5. Rule Evaluation
        ctx = EvaluationContext(
            timestamp=bundle.timestamp,
            current_exercise=exercise_name,
            vehicle_state=veh_state,
            detections=tracked_detections,
            frame_bundle=bundle,
            calibrations=self.calibrations,
        )
        new_events = self.rule_engine.evaluate(ctx)

        # 6. Apply Events
        for ev in new_events:
            self._handle_violation_event(ev)

        # 7. Check Finish Detection
        in_finish_zone = self.exercise_detector.is_in_finish_zone(veh_state.lat, veh_state.lon)
        if in_finish_zone and self.state_machine.current_state == ExamState.TEST_ACTIVE:
            self.state_machine.transition_to(ExamState.FINISH_DETECTED, "Finish zonasiga kirdi")

        if self.state_machine.current_state == ExamState.FINISH_DETECTED and veh_state.is_stopped:
            self.state_machine.transition_to(ExamState.VEHICLE_STOPPED, "Mashina finish zonasida to'xtadi")

        can_finish = (self.state_machine.current_state == ExamState.VEHICLE_STOPPED)

        # 8. Update HUD
        snap = self.scoring_engine.get_snapshot()
        self.active_test_screen.update_hud(
            elapsed_seconds=elapsed,
            speed_kmh=veh_state.speed_kmh,
            exercise=exercise_name,
            total_penalty=snap.total_penalty,
            violation_count=snap.confirmed_violations_count,
            can_finish=can_finish,
        )

    def _handle_violation_event(self, event) -> None:
        # Update Scoring
        self.scoring_engine.apply_event(event)

        # Record to Database
        if self.current_session_id:
            self.repository.record_violation(
                violation_id=event.violation_id,
                session_id=self.current_session_id,
                status=event.status,
                confidence=event.confidence,
                camera=event.camera,
                exercise=event.exercise,
                rule_code=event.rule_code,
                description=event.details,
            )
            if event.status == "CONFIRMED" and event.penalty > 0:
                self.repository.record_penalty(event.violation_id, self.current_session_id, event.penalty)

            # Record Evidence package asynchronously / cleanly
            self.evidence_recorder.record_evidence_package(self.current_session_id, event)

        # Enqueue Audio Voice Alert
        self.audio_service.enqueue_alert(
            voice_file=event.voice_file,
            voice_text=event.voice_text,
            critical=event.critical,
            rule_code=event.rule_code,
        )

        # Enqueue Screen Popup
        self.active_test_screen.popup_manager.enqueue(event)

        # Critical violation check
        if event.critical and self.state_machine.current_state == ExamState.TEST_ACTIVE:
            self._handle_critical_event(event.rule_code, event.details, event.timestamp)

    def _handle_critical_event(self, rule_code: str, details: str, timestamp: float) -> None:
        self._loop_timer.stop()
        self.state_machine.transition_to(ExamState.CRITICAL_VIOLATION, f"Kritik qoidabuzarlik: {rule_code}")
        self.state_machine.transition_to(ExamState.TERMINATED, "Test darhol to'xtatildi")
        self._finalize_and_show_results()

    def _finish_test(self) -> None:
        self._loop_timer.stop()
        if self.state_machine.current_state == ExamState.VEHICLE_STOPPED:
            self.state_machine.transition_to(ExamState.FINALIZING, "Imtihon yakunlanmoqda")
        self._finalize_and_show_results()

    def _finalize_and_show_results(self) -> None:
        snap = self.scoring_engine.get_snapshot()
        result_str = "PASS" if snap.is_passing else "FAIL"

        if self.current_session_id:
            self.repository.finalize_test_result(
                session_id=self.current_session_id,
                final_score=snap.current_score,
                result=result_str,
                critical_count=snap.critical_violations_count,
                suspect_count=snap.suspect_events_count,
            )

        self.state_machine.transition_to(ExamState.RESULT_READY, "Natija hisoblandi")
        self.state_machine.transition_to(ExamState.COMPLETED, "Imtihon to'liq yakunlandi")

        # Fetch violations for display
        violations = self.repository.get_violations_for_session(self.current_session_id or "")
        self.result_screen.display_result(
            final_score=snap.current_score,
            is_pass=snap.is_passing,
            violations=violations,
        )
        self.stack.setCurrentWidget(self.result_screen)

    def _export_pdf(self) -> None:
        if not self.current_session_id:
            return
        sess = self.repository.get_session(self.current_session_id) or {}
        violations = self.repository.get_violations_for_session(self.current_session_id)
        out_pdf = Path(self.config.storage.base_dir) / "reports" / f"Report_{self.current_session_id}.pdf"
        generate_pdf_report(
            output_path=out_pdf,
            session_data=sess,
            student_data=self.current_student_data,
            vehicle_data={"model": "Chevrolet Cobalt", "plate_number": "01 A 777 AA"},
            violations=violations,
            root_hash=sess.get("session_hash", ""),
        )

    def _export_usb(self) -> None:
        if self.current_session_id:
            self.storage_manager.export_session_to_usb(self.current_session_id, Path(self.config.storage.base_dir) / "usb_mount")

    def _reset_to_home(self) -> None:
        self.state_machine.transition_to(ExamState.READY, "Yangi talaba uchun tayyor")
        self.current_session_id = None
        self.scoring_engine = ScoringEngine(self.config.scoring)
        self.stack.setCurrentWidget(self.home_screen)
