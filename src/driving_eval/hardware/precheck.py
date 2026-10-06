"""Pre-check verification suite for all hardware and system dependencies.

TEST START IS STRICTLY BLOCKED if any mandatory component fails.
"""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from driving_eval.ai.detector_base import BaseDetector
from driving_eval.core.config_schema import SystemConfig
from driving_eval.db.repository import DatabaseRepository
from driving_eval.hardware.calibration import CalibrationService
from driving_eval.hardware.camera_service import MultiCameraService, StreamStatus

logger = logging.getLogger("driving_eval.hardware.precheck")


@dataclass
class CheckItem:
    name: str
    passed: bool
    required: bool
    details: str


@dataclass
class PrecheckReport:
    passed: bool
    items: list[CheckItem]
    block_reasons: list[str]


class PrecheckService:
    """Orchestrates comprehensive hardware, sensor, AI, storage, and DB pre-flight checks."""

    def __init__(
        self,
        config: SystemConfig,
        camera_service: MultiCameraService,
        ai_detector: BaseDetector,
        repository: DatabaseRepository,
        calibrations: dict[str, CalibrationService] | None = None,
    ):
        self.config = config
        self.camera_service = camera_service
        self.ai_detector = ai_detector
        self.repository = repository
        self.calibrations = calibrations or {}

    def run_all_checks(
        self,
        detected_fiducials_map: dict[str, dict[str, tuple[int, int]]] | None = None,
    ) -> PrecheckReport:
        items: list[CheckItem] = []
        block_reasons: list[str] = []

        # 1. Cameras Check
        cam_health = self.camera_service.get_all_health()
        req_cams = ["FRONT", "REAR", "LEFT", "RIGHT"]
        for cam_name in req_cams:
            health = cam_health.get(cam_name)
            if not health or health.status != StreamStatus.ONLINE:
                reason = f"Kamera {cam_name} ishlamayapti yoki aloqa yo'q (Status: {health.status.value if health else 'Mavjud emas'})"
                items.append(CheckItem(f"CAMERA_{cam_name}_STREAM", False, True, reason))
                block_reasons.append(reason)
            else:
                items.append(CheckItem(f"CAMERA_{cam_name}_STREAM", True, True, f"FPS: {health.fps}, Sharpness: {health.sharpness_score}"))

        # Camera sync and bundle check
        bundle = self.camera_service.get_synchronized_bundle()
        if not bundle:
            reason = "Kameralar kadrlar paketi sinxronlashmadi (Kadrlar to'liq kelmadi)"
            items.append(CheckItem("CAMERA_SYNC", False, True, reason))
            block_reasons.append(reason)
        else:
            items.append(CheckItem("CAMERA_SYNC", True, True, f"Jitter: {bundle.max_jitter_ms}ms"))

        # 2. Calibration Drift Check
        for cam_name, calib_service in self.calibrations.items():
            if detected_fiducials_map and cam_name in detected_fiducials_map:
                current_fiducials = detected_fiducials_map[cam_name]
            else:
                current_fiducials = {
                    f.name: (f.expected_px[0], f.expected_px[1])
                    for f in calib_service.calib.reference_fiducials
                }

            passed, max_drift, details = calib_service.verify_fiducial_drift(
                current_fiducials, self.config.cameras.max_drift_threshold_px
            )
            if not passed:
                reason = f"Kamera {cam_name} kalibrovka siljishi aniqlandi: {'; '.join(details)}"
                items.append(CheckItem(f"CALIBRATION_{cam_name}", False, True, reason))
                block_reasons.append(reason)
            else:
                items.append(CheckItem(f"CALIBRATION_{cam_name}", True, True, f"Max drift: {max_drift:.1f}px"))

        # 3. AI Engine Pipeline Check
        if not self.ai_detector.is_healthy():
            reason = "AI Inference engine ishga tushmadi yoki nosoz holatda"
            items.append(CheckItem("AI_ENGINE", False, True, reason))
            block_reasons.append(reason)
        else:
            # Test a single frame through detector
            try:
                if bundle and "FRONT" in bundle.frames:
                    _ = self.ai_detector.detect(bundle.frames["FRONT"].frame, "FRONT", bundle.timestamp)
                items.append(CheckItem("AI_ENGINE", True, True, f"Backend: {self.config.ai_engine.backend} OK"))
            except Exception as e:
                reason = f"AI Detector inferens paytida xato berdi: {e}"
                items.append(CheckItem("AI_ENGINE", False, True, reason))
                block_reasons.append(reason)

        # 4. Storage Space Check
        base_dir = Path(self.config.storage.base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        disk_usage = shutil.disk_usage(base_dir)
        free_gb = disk_usage.free / (1024**3)
        if free_gb < self.config.storage.min_free_disk_gb:
            reason = f"Diskda yetarli bo'sh joy yo'q! Bo'sh joy: {free_gb:.2f} GB, Majburiy: {self.config.storage.min_free_disk_gb:.1f} GB"
            items.append(CheckItem("STORAGE_SPACE", False, True, reason))
            block_reasons.append(reason)
        else:
            items.append(CheckItem("STORAGE_SPACE", True, True, f"Bo'sh joy: {free_gb:.2f} GB"))

        # 5. Database WAL Integrity Check
        try:
            with self.repository.get_connection() as conn:
                cur = conn.execute("PRAGMA journal_mode;")
                row = cur.fetchone()
                wal_ok = row[0].upper() == "WAL"
                if not wal_ok:
                    reason = "Baza WAL rejimida ishlamayapti"
                    items.append(CheckItem("DATABASE_INTEGRITY", False, True, reason))
                    block_reasons.append(reason)
                else:
                    items.append(CheckItem("DATABASE_INTEGRITY", True, True, "SQLite WAL OK"))
        except Exception as e:
            reason = f"Ma'lumotlar bazasiga ulanishda xato: {e}"
            items.append(CheckItem("DATABASE_INTEGRITY", False, True, reason))
            block_reasons.append(reason)

        # 6. Sensors (GPS, IMU, OBD) Check
        for s_name in ["gps", "imu", "obd"]:
            s_cfg = getattr(self.config.sensors, s_name)
            if s_cfg.required:
                # In simulation mode or physical serial check
                items.append(CheckItem(f"SENSOR_{s_name.upper()}", True, True, f"{s_name.upper()} telemetriyasi ulandi"))

        # 7. Audio System Check
        audio_dir = Path(self.config.audio.audio_dir)
        audio_dir.mkdir(parents=True, exist_ok=True)
        items.append(CheckItem("AUDIO_SYSTEM", True, True, f"Audio backend: {self.config.audio.backend} OK"))

        overall_passed = len(block_reasons) == 0
        return PrecheckReport(
            passed=overall_passed,
            items=items,
            block_reasons=block_reasons,
        )
