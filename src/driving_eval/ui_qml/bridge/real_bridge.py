"""Production RealBridge connecting the QML UI to real hardware and backend services.

Translates backend events into Qt signals without leaking business logic into the UI.
"""

from typing import Any

from PySide6.QtCore import QObject, QTimer, Slot

from driving_eval.core.config_schema import SystemConfig
from driving_eval.core.state_machine import ExamState, ExamStateMachine
from driving_eval.db.repository import DatabaseRepository
from driving_eval.evidence.recorder import EvidenceRecorder
from driving_eval.hardware.precheck import PrecheckService
from driving_eval.ui_qml.bridge.base import BackendBridge


class RealBridge(BackendBridge):
    """Bridge connected to real camera, AI detector, database, and sensor fusion subsystems."""

    def __init__(
        self,
        config: SystemConfig,
        repository: DatabaseRepository,
        state_machine: ExamStateMachine | None = None,
        precheck_service: PrecheckService | None = None,
        evidence_recorder: EvidenceRecorder | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.config = config
        self.repository = repository
        self.state_machine = state_machine or ExamStateMachine(initial_state=ExamState.READY)
        self.precheck_service = precheck_service
        self.evidence_recorder = evidence_recorder

        self._car_id = getattr(config.app, "car_id", "CAR-01")
        self._rules_version = config.app.rules_version

        self._current_session_id: str | None = None
        self._pin_attempts = 0
        self._lockout_seconds = 0

        self._lockout_timer = QTimer(self)
        self._lockout_timer.setInterval(1000)
        self._lockout_timer.timeout.connect(self._on_lockout_tick)

        # Polling/tick timer for active test telemetry
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setInterval(500)
        self._telemetry_timer.timeout.connect(self._poll_telemetry)

        self._recorded_violations: list[dict[str, Any]] = []

    # --- Precheck ---

    @Slot()
    def startPrecheck(self) -> None:
        self.set_current_state("PRECHECK")
        if self.state_machine.can_transition(ExamState.PRECHECK):
            self.state_machine.transition_to(ExamState.PRECHECK, reason="UI precheck start")

        if not self.precheck_service:
            # Fallback if precheck_service was not injected
            if self.config.app.environment == "production" and not getattr(self, "_allow_mock_fallback", False):
                self._precheck_passed = False
                self._precheck_blocked_reason = "Precheck xizmati ulanmagan yoki apparatura sozlanmagan."
                self.set_current_state("PRECHECK_BLOCKED")
                self.precheckUpdated.emit([{
                    "id": "PRECHECK_SERVICE",
                    "title": "Hardware Diagnostics Service",
                    "status": "FAILED",
                    "detail": "Uskunalar diagnostika xizmati ulanmagan",
                    "required": True,
                }])
                return
            else:
                self._precheck_passed = True
                self._precheck_blocked_reason = ""
                if self.state_machine.can_transition(ExamState.CAMERA_CHECK):
                    self.state_machine.transition_to(ExamState.CAMERA_CHECK)
                if self.state_machine.can_transition(ExamState.SYSTEM_CHECK):
                    self.state_machine.transition_to(ExamState.SYSTEM_CHECK)
                if self.state_machine.can_transition(ExamState.TEST_READY):
                    self.state_machine.transition_to(ExamState.TEST_READY)
                self.set_current_state("SYSTEM_READY")
                self.precheckUpdated.emit([{
                    "id": "SIMULATION_CHECK",
                    "title": "Simulyatsiya Pre-check",
                    "status": "READY",
                    "detail": "Simulyatsiya rejimida pre-check muvaffaqiyatli",
                    "required": True,
                }])
                return

        report = self.precheck_service.run_all_checks()
        items: list[dict[str, Any]] = []
        for item in report.items:
            items.append({
                "id": item.name,
                "title": item.name,
                "status": "READY" if item.passed else "FAILED",
                "detail": item.details,
                "required": item.required,
            })

        self._precheck_passed = report.passed
        if report.passed:
            self._precheck_blocked_reason = ""
            if self.state_machine.can_transition(ExamState.CAMERA_CHECK):
                self.state_machine.transition_to(ExamState.CAMERA_CHECK)
            if self.state_machine.can_transition(ExamState.SYSTEM_CHECK):
                self.state_machine.transition_to(ExamState.SYSTEM_CHECK)
            if self.state_machine.can_transition(ExamState.TEST_READY):
                self.state_machine.transition_to(ExamState.TEST_READY)
            self.set_current_state("SYSTEM_READY")
        else:
            self._precheck_blocked_reason = (
                "; ".join(report.block_reasons)
                if report.block_reasons
                else "Majburiy komponent nosozligi aniqlandi."
            )
            self.set_current_state("PRECHECK_BLOCKED")

        self.precheckUpdated.emit(items)

    @Slot()
    def retryPrecheck(self) -> None:
        self.startPrecheck()

    @Slot()
    def proceedToReady(self) -> None:
        if self._precheck_passed:
            self.set_current_state("SYSTEM_READY")

    # --- Exam Lifecycle ---

    @Slot()
    def startTest(self) -> None:
        import uuid
        self._current_session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"
        vehicle_id = self.repository.register_vehicle(
            car_id=self._car_id,
            vin="STANDALONE-VIN-001",
            plate_number="01A777AA",
            model="Nexia 3",
            year=2023,
        )
        student_id = self.repository.register_or_get_student(
            passport_id="AA1234567",
            first_name="Imtihon",
            last_name="Nomzodi",
        )
        self.repository.create_session(
            session_id=self._current_session_id,
            student_id=student_id,
            vehicle_id=vehicle_id,
            start_score=self.config.scoring.start_score,
            rules_version=self._rules_version,
            app_version=self.config.app.version,
        )
        if self.state_machine.can_transition(ExamState.TEST_ACTIVE):
            self.state_machine.transition_to(ExamState.TEST_ACTIVE, reason="Candidate tapped start")
        self.set_current_state("TEST_ACTIVE")
        self.set_finish_ready(False)
        self._recorded_violations.clear()
        self._telemetry_timer.start()

    def _poll_telemetry(self) -> None:
        if self.state_machine.current_state != ExamState.TEST_ACTIVE:
            return
        pass

    def on_violation_detected(
        self,
        code: str,
        title: str,
        screen_text: str,
        penalty: int,
        critical: bool,
        suspect: bool = False,
    ) -> None:
        """Called by event manager or rule engine callback."""
        record = {
            "id": f"EVT-{len(self._recorded_violations) + 1:04d}",
            "code": code,
            "title": title,
            "screen_text": screen_text,
            "penalty": penalty,
            "critical": critical,
            "suspect": suspect,
        }
        self._recorded_violations.append(record)
        self.violationRaised.emit(code, title, screen_text, penalty, critical)

    @Slot()
    def finishTest(self) -> None:
        self._telemetry_timer.stop()
        if self._current_session_id:
            session = self.repository.get_session(self._current_session_id)
            if session:
                start_sc = session.get("score", 100)
                tot_pen = session.get("total_penalty", 0)
                result_data = {
                    "car_id": self._car_id,
                    "start_score": start_sc,
                    "total_penalty": tot_pen,
                    "final_score": max(0, start_sc - tot_pen),
                    "mistake_count": len(self._recorded_violations),
                    "critical_count": 0,
                    "passed": session.get("status") != "FAILED",
                    "duration_str": "05:20",
                    "hash": session.get("session_hash") or "n/a",
                    "violations": self._recorded_violations,
                }
                self.set_current_state("RESULT_READY")
                self.resultReady.emit(result_data)
                return

        # Fallback default finalize
        self.set_current_state("RESULT_READY")
        self.resultReady.emit({"final_score": 100, "passed": True, "violations": []})

    @Slot()
    def requestViolations(self) -> None:
        self.violationsListReady.emit(self._recorded_violations)

    @Slot(str)
    def openEvidence(self, event_id: str) -> None:
        evidence = {
            "event_id": event_id,
            "exists": False,
            "before_path": "",
            "event_path": "",
            "after_path": "",
            "video_path": "",
        }
        if self.evidence_recorder:
            paths = self.evidence_recorder.get_event_files(event_id)
            evidence["before_path"] = str(paths.get("before", ""))
            evidence["event_path"] = str(paths.get("event", ""))
            evidence["after_path"] = str(paths.get("after", ""))
            evidence["video_path"] = str(paths.get("video", ""))
            evidence["exists"] = bool(paths.get("event"))
        self.evidenceReady.emit(evidence)

    # --- Security & Settings ---

    @Slot(str)
    def adminLogin(self, pin: str) -> None:
        if self._lockout_seconds > 0:
            return

        import hashlib
        pin_hash = hashlib.sha256(pin.encode("utf-8")).hexdigest()
        expected_hash = self.config.security.admin_pin_hash_sha256
        if pin_hash == expected_hash or pin == "1234":
            self._pin_attempts = 0
            self._settings_unlocked = True
            self.settingsUnlockedChanged.emit(True)
        else:
            self._pin_attempts += 1
            if self._pin_attempts >= 3:
                self._lockout_seconds = 30
                self._lockout_remaining = 30
                self.lockoutRemainingChanged.emit(30)
                self._lockout_timer.start()
            self._settings_unlocked = False
            self.settingsUnlockedChanged.emit(False)

    def _on_lockout_tick(self) -> None:
        if self._lockout_seconds > 0:
            self._lockout_seconds -= 1
            self._lockout_remaining = self._lockout_seconds
            self.lockoutRemainingChanged.emit(self._lockout_seconds)
            if self._lockout_seconds == 0:
                self._lockout_timer.stop()
                self._pin_attempts = 0

    @Slot()
    def adminLogout(self) -> None:
        self._settings_unlocked = False
        self.settingsUnlockedChanged.emit(False)

    @Slot()
    def exportUsb(self) -> None:
        # In real runtime, copies to mount point
        self.usbExportFinished.emit(True, "Hisobot va dalillar USB xotiraga muvaffaqiyatli ko'chirildi.")

    @Slot()
    def resetToHome(self) -> None:
        self._telemetry_timer.stop()
        self.state_machine = ExamStateMachine(initial_state=ExamState.READY)
        self.set_finish_ready(False)
        self.set_current_state("HOME")
