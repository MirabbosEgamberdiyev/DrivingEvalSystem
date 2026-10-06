"""Scripted deterministic MockBridge for standalone QML UI testing and interactive simulation.

Simulates the full lifecycle including:
- Normal test with passing score
- Camera failure & retry recovery
- Two back-to-back violations testing the UI popup queue
- Critical violation immediately terminating the test
- PASS and FAIL final results
- Disconnect & reconnect recovery
- Touch PIN security with 3-attempt lockout
"""

from typing import Any

from PySide6.QtCore import QObject, QTimer, Slot

from driving_eval.ui_qml.bridge.base import BackendBridge


class MockBridge(BackendBridge):
    """Mock implementation of BackendBridge with deterministic scenario scripting."""

    def __init__(
        self,
        scenario: str = "normal_pass",
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.scenario = scenario
        self._pin_attempts = 0
        self._max_pin_attempts = 3
        self._correct_pin = "1234"
        self._lockout_seconds = 0

        # Telemetry state
        self._elapsed = 0
        self._speed = 0.0
        self._current_exercise = "BOSHLASH (START)"
        self._total_penalty = 0
        self._mistake_count = 0
        self._critical_count = 0

        # Scenario step timer
        self._test_timer = QTimer(self)
        self._test_timer.setInterval(1000)
        self._test_timer.timeout.connect(self._on_test_tick)

        # Lockout timer
        self._lockout_timer = QTimer(self)
        self._lockout_timer.setInterval(1000)
        self._lockout_timer.timeout.connect(self._on_lockout_tick)

        # Precheck state items
        self._precheck_items: list[dict[str, Any]] = []
        self._init_precheck_items()

        # Recorded violations history
        self._recorded_violations: list[dict[str, Any]] = []

    def _init_precheck_items(self) -> None:
        self._precheck_items = [
            {"id": "comp_cam_front", "title": "Old Kamera (FRONT)", "status": "CHECKING", "detail": "1920x1080 @ 30 FPS", "required": True},
            {"id": "comp_cam_rear", "title": "Orqa Kamera (REAR)", "status": "CHECKING", "detail": "1920x1080 @ 30 FPS", "required": True},
            {"id": "comp_cam_left", "title": "Chap Kamera (LEFT)", "status": "CHECKING", "detail": "1280x720 @ 30 FPS", "required": True},
            {"id": "comp_cam_right", "title": "O'ng Kamera (RIGHT)", "status": "CHECKING", "detail": "1280x720 @ 30 FPS", "required": True},
            {"id": "comp_cam_drift", "title": "Kameralar Kalibrovkasi (Drift)", "status": "CHECKING", "detail": "Siljish: 0.8% (<3%)", "required": True},
            {"id": "comp_ai_engine", "title": "AI Inference Dvigateli", "status": "CHECKING", "detail": "ONNX-Runtime Latency: 16ms", "required": True},
            {"id": "comp_gps", "title": "GPS / GNSS Moduli", "status": "CHECKING", "detail": "10 Hz, 14 Yo'ldosh, RTK Fix", "required": True},
            {"id": "comp_imu", "title": "IMU Akselerometr / Giroskop", "status": "CHECKING", "detail": "100 Hz 6-DOF Faol", "required": True},
            {"id": "comp_obd", "title": "OBD-II Telemetriya (CAN)", "status": "CHECKING", "detail": "500 kbps CAN avtobus ulandi", "required": True},
            {"id": "comp_storage", "title": "NVMe SSD Xotira Sig'imi", "status": "CHECKING", "detail": "428 GB bo'sh joy (>10 GB)", "required": True},
            {"id": "comp_database", "title": "SQLite WAL Ma'lumotlar Bazasi", "status": "CHECKING", "detail": "SHA-256 zanjir yaxlit", "required": True},
            {"id": "comp_audio", "title": "Ovozli Ogohlantirish Tizimi", "status": "CHECKING", "detail": "Offline ALSA / WAV Audio", "required": True},
        ]

    # --- Precheck Slots ---

    @Slot()
    def startPrecheck(self) -> None:
        """Runs precheck simulation."""
        self.set_current_state("PRECHECK")
        self._init_precheck_items()
        self.precheckUpdated.emit(self._precheck_items)

        # Simulate progressive component checking
        QTimer.singleShot(400, self._complete_precheck)

    def _complete_precheck(self) -> None:
        fail_camera = (self.scenario == "camera_fail")
        for item in self._precheck_items:
            if fail_camera and item["id"] == "comp_cam_rear":
                item["status"] = "FAILED"
                item["detail"] = "Signal yo'q (Video stream timeout)"
            else:
                item["status"] = "READY"

        if fail_camera:
            self._precheck_passed = False
            self._precheck_blocked_reason = "Orqa kamera (REAR) ishlamayapti. Testni boshlash mumkin emas."
            self.set_current_state("PRECHECK_BLOCKED")
        else:
            self._precheck_passed = True
            self._precheck_blocked_reason = ""
            self.set_current_state("SYSTEM_READY")

        self.precheckUpdated.emit(self._precheck_items)

    @Slot()
    def retryPrecheck(self) -> None:
        """Retries precheck and recovers from simulated failure."""
        self.scenario = "normal_pass"  # recover
        self.startPrecheck()

    @Slot()
    def proceedToReady(self) -> None:
        """Manually moves to SYSTEM_READY if precheck passed."""
        if self._precheck_passed:
            self.set_current_state("SYSTEM_READY")

    # --- Exam Lifecycle Slots ---

    @Slot()
    def startTest(self) -> None:
        """Transitions into TEST_ACTIVE and starts telemetry simulation."""
        self._elapsed = 0
        self._speed = 0.0
        self._current_exercise = "BOSHLASH (START)"
        self._total_penalty = 0
        self._mistake_count = 0
        self._critical_count = 0
        self.set_finish_ready(False)
        self._recorded_violations.clear()

        self.set_current_state("TEST_ACTIVE")
        self.liveStatusUpdated.emit(0, 0.0, self._current_exercise, 0, 0)
        self._test_timer.start()

    def _on_test_tick(self) -> None:
        if self._current_state != "TEST_ACTIVE":
            return

        self._elapsed += 1

        # Simulate speed and exercises across time
        if self._elapsed == 1:
            self._speed = 12.0
            self._current_exercise = "ESTAKADA"
        elif self._elapsed == 3:
            self._speed = 18.5
            self._current_exercise = "ZMEIKA"
        elif self._elapsed == 5:
            # Trigger first violation
            self._raise_violation(
                code="CONE_TOUCH",
                title="Konusga tegish",
                screen_text="Konusga tegish holati aniqlandi",
                penalty=10,
                critical=False,
            )
        elif self._elapsed == 6 and self.scenario == "double_violation":
            # Immediately trigger second violation to test UI queue
            self._raise_violation(
                code="LINE_TOUCH",
                title="Chiziq bosish",
                screen_text="Yon chiziq ustiga chiqib ketildi",
                penalty=5,
                critical=False,
            )
        elif self._elapsed == 7:
            if self.scenario == "critical_fail":
                self._raise_violation(
                    code="STOP_LINE_FAIL",
                    title="Stop chizig'ida to'xtamaslik",
                    screen_text="Kritik xato: Stop chizig'ida to'xtamadi",
                    penalty=100,
                    critical=True,
                )
                self._test_timer.stop()
                self._finalize_result()
                return
            self._speed = 14.0
            self._current_exercise = "PARALLEL PARK"
        elif self._elapsed == 9:
            self._speed = 4.0
            self._current_exercise = "YAKUNLASH (FINISH)"
        elif self._elapsed >= 10:
            self._speed = 0.0
            self.set_finish_ready(True)

        self.liveStatusUpdated.emit(
            self._elapsed,
            self._speed,
            self._current_exercise,
            self._total_penalty,
            self._mistake_count,
        )

    def on_violation_detected(
        self,
        code: str,
        title: str,
        screen_text: str,
        penalty: int,
        critical: bool,
        suspect: bool = False,
    ) -> None:
        self._raise_violation(code, title, screen_text, penalty, critical, suspect)

    def _raise_violation(
        self,
        code: str,
        title: str,
        screen_text: str,
        penalty: int,
        critical: bool,
        suspect: bool = False,
    ) -> None:
        event_id = f"EVT-{len(self._recorded_violations) + 1:04d}"
        if not suspect:
            self._total_penalty += penalty
            self._mistake_count += 1
            if critical:
                self._critical_count += 1

        record = {
            "id": event_id,
            "code": code,
            "title": title,
            "screen_text": screen_text,
            "penalty": penalty,
            "critical": critical,
            "suspect": suspect,
            "exercise": self._current_exercise,
            "timestamp": f"{self._elapsed // 60:02d}:{self._elapsed % 60:02d}",
            "evidence_id": event_id,
        }
        self._recorded_violations.append(record)

        self.violationRaised.emit(code, title, screen_text, penalty, critical)

    @Slot()
    def finishTest(self) -> None:
        """Called when candidate taps finish in the vehicle stopped state."""
        if not self._finish_ready and self._current_state != "CRITICAL_VIOLATION":
            return
        self._test_timer.stop()
        self._finalize_result()

    def _finalize_result(self) -> None:
        start_score = 100
        pass_threshold = 70
        final_score = max(0, start_score - self._total_penalty)
        passed = (final_score >= pass_threshold) and (self._critical_count == 0)

        # Add a suspect event for inspector review demonstration
        if not any(v.get("suspect") for v in self._recorded_violations):
            self._recorded_violations.append({
                "id": "EVT-SUSP-01",
                "code": "PEDESTRIAN_SUSPECT",
                "title": "Piyodalar yo'lagi (Shubhali)",
                "screen_text": "Ishonchlilik 78% (<85% chegara) - jarima olinmadi",
                "penalty": 0,
                "critical": False,
                "suspect": True,
                "exercise": "ZMEIKA",
                "timestamp": "00:04",
                "evidence_id": "EVT-SUSP-01",
            })

        result_data = {
            "car_id": self._car_id,
            "start_score": start_score,
            "total_penalty": self._total_penalty,
            "final_score": final_score,
            "mistake_count": self._mistake_count,
            "critical_count": self._critical_count,
            "passed": passed,
            "duration_str": f"{self._elapsed // 60:02d}:{self._elapsed % 60:02d}",
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "violations": self._recorded_violations,
        }

        self.set_current_state("RESULT_READY")
        self.resultReady.emit(result_data)

    @Slot()
    def requestViolations(self) -> None:
        self.violationsListReady.emit(self._recorded_violations)

    @Slot(str)
    def openEvidence(self, event_id: str) -> None:
        """Simulates retrieving evidence paths for a violation."""
        evidence = {
            "event_id": event_id,
            "code": "CONE_TOUCH",
            "exercise": "ZMEIKA",
            "timestamp": "00:05",
            "before_path": "",
            "event_path": "",
            "after_path": "",
            "video_path": "",
            "exists": True,
        }
        self.evidenceReady.emit(evidence)

    # --- Settings / PIN Security ---

    @Slot(str)
    def adminLogin(self, pin: str) -> None:
        if self._lockout_seconds > 0:
            return

        if pin == self._correct_pin:
            self._pin_attempts = 0
            self._settings_unlocked = True
            self.settingsUnlockedChanged.emit(True)
        else:
            self._pin_attempts += 1
            if self._pin_attempts >= self._max_pin_attempts:
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
        """Simulates USB export."""
        QTimer.singleShot(800, lambda: self.usbExportFinished.emit(
            True, "USB ga eksport qilindi: /media/usb/EXAM_EXPORT_CAR01.zip"
        ))

    @Slot()
    def resetToHome(self) -> None:
        self._test_timer.stop()
        self._elapsed = 0
        self._speed = 0.0
        self._total_penalty = 0
        self._mistake_count = 0
        self._critical_count = 0
        self.set_finish_ready(False)
        self.set_current_state("HOME")

    # --- Offline Disconnect Simulation Helper ---

    def simulate_disconnect(self, duration_ms: int = 3000) -> None:
        """Simulates brief network/daemon disconnection."""
        self.set_is_connected(False)
        QTimer.singleShot(duration_ms, lambda: self.set_is_connected(True))
