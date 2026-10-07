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
            {"id": "comp_obd", "title": "OBD-II Telemetriya (CAN)", "status": "CHECKING", "detail": "500 kbps CAN shina ulandi", "required": True},
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

    @Slot(str)
    def startTestWithMode(self, mode: str) -> None:
        """Sets active examination mode and begins test."""
        self.set_exam_mode(mode)
        self.startTest()

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
                if self._exam_mode == "ASSESSMENT":
                    self._test_timer.stop()
                    self._finalize_result()
                    return
                # In TRAINING mode, alert is raised but session continues without abrupt abort
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
            "mode": self._exam_mode,
            "official": self._exam_mode == "ASSESSMENT",
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

    @Slot()
    def requestSessions(self) -> None:
        """Simulates historical session list for Inspector Mode."""
        mock_sessions = [
            {
                "id": "SES-9821A4B0",
                "passport_id": "AA1234567",
                "first_name": "Alisher",
                "last_name": "Navoiy",
                "created_at": "2026-10-07 09:15:22",
                "final_score": 90,
                "result": "PASS",
                "status": "COMPLETED",
                "violations_count": 1,
                "suspect_count": 0,
                "duration": "08:14",
                "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            },
            {
                "id": "SES-8412F1C2",
                "passport_id": "AB7654321",
                "first_name": "Bobur",
                "last_name": "Mirzo",
                "created_at": "2026-10-07 08:30:10",
                "final_score": 65,
                "result": "FAIL",
                "status": "COMPLETED",
                "violations_count": 3,
                "suspect_count": 1,
                "duration": "11:05",
                "hash": "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
            },
            {
                "id": "SES-7104E391",
                "passport_id": "AC9876543",
                "first_name": "Nodira",
                "last_name": "Begim",
                "created_at": "2026-10-06 16:45:00",
                "final_score": 0,
                "result": "FAIL",
                "status": "CRITICAL_FAIL",
                "violations_count": 1,
                "suspect_count": 0,
                "duration": "03:12",
                "hash": "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce",
            },
            {
                "id": "SES-6530B218",
                "passport_id": "AD5432109",
                "first_name": "Temur",
                "last_name": "Barlos",
                "created_at": "2026-10-06 14:10:45",
                "final_score": 85,
                "result": "PASS",
                "status": "COMPLETED",
                "violations_count": 2,
                "suspect_count": 1,
                "duration": "09:40",
                "hash": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
            },
        ]
        self.sessionsListReady.emit(mock_sessions)

    @Slot()
    def requestDiagnostics(self) -> None:
        """Emits rich live diagnostics telemetry for Admin/Maintenance Mode."""
        data = {
            "cpu_usage_pct": 28.4,
            "ram_usage_pct": 42.1,
            "disk_free_gb": 428.5,
            "system_temp_c": 46.2,
            "cameras": [
                {"name": "FRONT", "status": "ONLINE", "fps": 30.0, "latency_ms": 16.4, "sharpness": 145.0},
                {"name": "REAR", "status": "ONLINE", "fps": 30.0, "latency_ms": 17.2, "sharpness": 139.2},
                {"name": "LEFT", "status": "ONLINE", "fps": 30.0, "latency_ms": 15.9, "sharpness": 142.8},
                {"name": "RIGHT", "status": "ONLINE", "fps": 30.0, "latency_ms": 16.1, "sharpness": 140.5},
            ],
            "calibration_quality": {"FRONT": 98.4, "REAR": 97.2, "LEFT": 96.8, "RIGHT": 98.1},
            "gps": {"status": "FIX_OK", "satellites": 14, "fix_type": "3D RTK Fix", "lat": 41.311081, "lon": 69.240562},
            "obd": {"status": "CONNECTED", "protocol": "CAN ISO 15765-4", "rpm": 850, "speed_kmh": 0.0},
            "imu": {"status": "ACTIVE", "sample_rate": 100, "pitch_deg": 0.2, "roll_deg": -0.1},
            "ai": {"backend": "DirectML (GPU)", "fps": 45.0, "latency_ms": 18.2},
            "license": {"valid": True, "type": "STANDALONE_COMMERCIAL", "expires": "2027-12-31"},
        }
        self.systemDiagnosticsUpdated.emit(data)

    @Slot(str)
    def verifySessionHash(self, session_id: str) -> None:
        """Simulates hash chain and Ed25519 signature verification."""
        QTimer.singleShot(400, lambda: self.hashVerificationFinished.emit(
            session_id, True, "SHA-256 zanjir va Ed25519 imzo tasdiqlandi (100% haqiqiy)."
        ))

    @Slot(str)
    def exportSessionPdf(self, session_id: str) -> None:
        """Simulates official PDF report export."""
        QTimer.singleShot(600, lambda: self.reportExportFinished.emit(
            True, f"PDF Bayonnoma tayyorlandi: data/reports/bayonnoma_{session_id}.pdf"
        ))

    @Slot(result=dict)
    def getAutodromeConfig(self) -> dict[str, Any]:
        """Loads and returns polygon configuration from autodrome.json."""
        import json
        from pathlib import Path

        config_path = Path("config/autodrome.json")
        if not config_path.exists():
            return {
                "name": "Tashkent Central Autodrome",
                "datum": "WGS84",
                "base_lat": 41.311081,
                "base_lon": 69.240562,
                "summary": "Poligon: Tashkent Central Autodrome (WGS84 | Lat: 41.311081, Lon: 69.240562)",
            }
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            base_coords = data.get("base_coordinates", {})
            lat = base_coords.get("lat", 41.311081)
            lon = base_coords.get("lon", 69.240562)
            name = data.get("autodrome_name", "Tashkent Central Autodrome")
            datum = data.get("datum", "WGS84")
            return {
                "name": name,
                "datum": datum,
                "base_lat": lat,
                "base_lon": lon,
                "summary": f"Poligon: {name} ({datum} Datum | Lat: {lat}, Lon: {lon})",
            }
        except Exception:
            return {
                "name": "Tashkent Central Autodrome",
                "datum": "WGS84",
                "base_lat": 41.311081,
                "base_lon": 69.240562,
                "summary": "Poligon: Tashkent Central Autodrome",
            }

    @Slot(result=list)
    def getAutodromeExercises(self) -> list[dict[str, Any]]:
        """Loads and returns 8 polygon exercises dynamically from autodrome.json."""
        import json
        from pathlib import Path

        config_path = Path("config/autodrome.json")
        if not config_path.exists():
            return []
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            sequence = data.get("sequence", [])
            zones = data.get("zones", {})
            exercises = []
            for i, code in enumerate(sequence, start=1):
                zone = zones.get(code, {})
                radius = zone.get("radius_meters", 18.0)
                desc = zone.get("name_uz", code)
                exercises.append({
                    "id": code,
                    "name": f"{i}. {code}",
                    "desc": desc,
                    "active": True,
                    "radius": f"{radius:.0f} m",
                    "lat": zone.get("lat", 0.0),
                    "lon": zone.get("lon", 0.0),
                    "expected_heading": zone.get("expected_heading_deg", 0.0),
                })
            return exercises
        except Exception:
            return []

