"""Pydantic v2 schemas for strict configuration validation.

Validates config.yaml, rules.yaml, car.yaml, and calibration files.
Prevents system boot if any configuration parameter is missing or invalid.
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from driving_eval.core.exceptions import ConfigurationError, RulesValidationError

# --- Application & System Configurations ---

class AppConfig(BaseModel):
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    rules_version: str = Field(..., min_length=1)
    environment: Literal["production", "simulation"] = "production"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: str = "data/logs/system.log"
    supported_languages: list[str] = Field(default_factory=lambda: ["uz-Latn", "uz-Cyrl", "ru"])
    default_language: str = "uz-Latn"


class ScoringConfig(BaseModel):
    start_score: int = Field(default=100, ge=1, le=100)
    pass_score: int = Field(default=80, ge=1, le=100)
    max_critical_allowed: int = Field(default=0, ge=0, le=0)
    allow_suspect_penalty: bool = False

    @field_validator("pass_score")
    @classmethod
    def validate_pass_score(cls, v: int, info: Any) -> int:
        return v


class CameraDeviceConfig(BaseModel):
    name: str = Field(description="Camera identifier, e.g. FRONT, REAR, LEFT, RIGHT, CABIN")
    device_index: int = Field(default=0, ge=0)
    stream_uri: str = ""
    sim_video_path: str = ""
    width: int = Field(default=1280, ge=320)
    height: int = Field(default=720, ge=240)
    fps: int = Field(default=30, ge=10, le=120)
    required: bool = True


class CamerasConfig(BaseModel):
    sync_tolerance_ms: float = Field(default=66.0, gt=0.0)
    min_operational_fps: float = Field(default=20.0, gt=5.0)
    max_drift_threshold_px: float = Field(default=15.0, gt=0.0)
    devices: dict[str, CameraDeviceConfig]

    @field_validator("devices")
    @classmethod
    def validate_required_cameras(cls, v: dict[str, CameraDeviceConfig]) -> dict[str, CameraDeviceConfig]:
        if not v:
            raise ValueError("Kamida 1 ta kamera konfiguratsiyasi mavjud bo'lishi shart")
        return v


class AIEngineConfig(BaseModel):
    backend: Literal["mock", "onnx", "tensorrt"] = "mock"
    model_path: str = "models/yolo_driving_v1.onnx"
    confidence_threshold: float = Field(default=0.70, ge=0.1, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.1, le=1.0)
    input_size: list[int] = Field(default_factory=lambda: [640, 640])
    device: Literal["cuda", "cpu"] = "cpu"


class SensorDeviceConfig(BaseModel):
    enabled: bool = True
    port: str = ""
    baudrate: int = Field(default=9600, gt=0)
    required: bool = True
    sim_mode: bool = True


class SensorsConfig(BaseModel):
    gps: SensorDeviceConfig
    imu: SensorDeviceConfig
    obd: SensorDeviceConfig


class ExercisesConfig(BaseModel):
    sequence: list[str] = Field(..., min_length=1)
    geofence_tolerance_meters: float = Field(default=3.0, gt=0.0)
    speed_stop_threshold_kmh: float = Field(default=1.5, ge=0.0)
    autodrome_map_file: str | None = Field(default="config/autodrome.json")


class StorageConfig(BaseModel):
    base_dir: str = "data"
    db_path: str = "data/db/exam_system.db"
    evidence_dir: str = "data/evidence"
    min_free_disk_gb: float = Field(default=10.0, gt=0.0)
    prune_threshold_gb: float = Field(default=5.0, gt=0.0)
    ring_buffer_seconds: float = Field(default=5.0, gt=1.0)


class AudioConfig(BaseModel):
    enabled: bool = True
    backend: Literal["wav_primary", "piper_tts"] = "wav_primary"
    audio_dir: str = "data/audio/uz"
    piper_model_path: str = "models/piper/uz_model.onnx"
    volume: float = Field(default=1.0, ge=0.0, le=1.0)


class UIConfig(BaseModel):
    kiosk_mode: bool = True
    fullscreen: bool = True
    window_title: str = "Avtomatlashtirilgan Haydash Imtihon Tizimi"
    popup_duration_seconds: float = Field(default=3.5, ge=1.0, le=10.0)
    language: str = "uz"


class SecurityConfig(BaseModel):
    admin_pin_pbkdf2: str = ""
    admin_pin_salt: str = ""
    admin_pin_hash_sha256: str = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
    lockout_duration_seconds: int = Field(default=300, ge=10)  # 5 minutes default lockout
    max_failed_attempts: int = Field(default=3, ge=1)
    power_loss_recovery_mode: Literal["SAFE_INTERRUPT", "RESUME_ACTIVE"] = "SAFE_INTERRUPT"


class SystemConfig(BaseModel):
    app: AppConfig
    scoring: ScoringConfig
    cameras: CamerasConfig
    ai_engine: AIEngineConfig
    sensors: SensorsConfig
    exercises: ExercisesConfig
    storage: StorageConfig
    audio: AudioConfig
    ui: UIConfig
    security: SecurityConfig

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> "SystemConfig":
        p = Path(path)
        if not p.exists():
            raise ConfigurationError(f"Config fayli topilmadi: {p.resolve()}")
        try:
            with open(p, encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
            return cls.model_validate(raw_data)
        except Exception as e:
            raise ConfigurationError(f"Config validatsiyadan o'tmadi ({p}): {e}") from e


# --- Rules Manifest Schema ---

class RuleTranslation(BaseModel):
    title: str = Field(..., min_length=2)
    screen_text: str = Field(..., min_length=2)
    voice_file: str = Field(..., min_length=2)
    voice_text: str = Field(..., min_length=2)
    reviewed: bool = True
    reviewer: str = "methodologist"


class RuleItem(BaseModel):
    code: str = Field(..., min_length=2)
    title: str = ""
    screen_text: str = ""
    voice_file: str = ""
    voice_text: str = ""
    penalty: int = Field(..., ge=0, le=100)
    critical: bool = False
    debounce_frames: int = Field(default=5, ge=1, le=100)
    cooldown_seconds: float = Field(default=5.0, ge=0.0)
    min_confidence: float = Field(default=0.80, ge=0.0, le=1.0)
    exercise_binding: list[str] = Field(default_factory=list)
    translations: dict[str, RuleTranslation] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def sync_translations(cls, data: Any) -> Any:
        if isinstance(data, dict):
            trans = data.get("translations", {})
            if trans and not data.get("title"):
                ref = trans.get("uz-Latn") or next(iter(trans.values()))
                if isinstance(ref, dict):
                    data.setdefault("title", ref.get("title", ""))
                    data.setdefault("screen_text", ref.get("screen_text", ""))
                    data.setdefault("voice_file", ref.get("voice_file", ""))
                    data.setdefault("voice_text", ref.get("voice_text", ""))
            elif data.get("title") and not trans:
                data["translations"] = {
                    "uz-Latn": {
                        "title": data["title"],
                        "screen_text": data.get("screen_text", ""),
                        "voice_file": data.get("voice_file", ""),
                        "voice_text": data.get("voice_text", ""),
                        "reviewed": True,
                        "reviewer": "default",
                    }
                }
        return data

    def get_title(self, lang: str = "uz-Latn") -> str:
        if lang in self.translations:
            return self.translations[lang].title
        return self.title or self.code

    def get_screen_text(self, lang: str = "uz-Latn") -> str:
        if lang in self.translations:
            return self.translations[lang].screen_text
        return self.screen_text or self.code

    def get_voice_text(self, lang: str = "uz-Latn") -> str:
        if lang in self.translations:
            return self.translations[lang].voice_text
        return self.voice_text or self.code

    def get_voice_file(self, lang: str = "uz-Latn") -> str:
        if lang in self.translations:
            return self.translations[lang].voice_file
        return self.voice_file or f"{self.code.lower()}.wav"


class RulesManifest(BaseModel):
    version: str = Field(..., min_length=1)
    last_updated: str = Field(..., min_length=1)
    description: str = ""
    rules: list[RuleItem] = Field(..., min_length=1)

    def get_rule(self, code: str) -> RuleItem | None:
        for rule in self.rules:
            if rule.code == code:
                return rule
        return None

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> "RulesManifest":
        p = Path(path)
        if not p.exists():
            raise RulesValidationError(f"Rules fayli topilmadi: {p.resolve()}")
        try:
            with open(p, encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
            manifest = cls.model_validate(raw_data)
            # Duplicate code check
            codes = [r.code for r in manifest.rules]
            if len(codes) != len(set(codes)):
                duplicates = [c for c in codes if codes.count(c) > 1]
                raise RulesValidationError(f"rules.yaml da takrorlangan qoida kodlari mavjud: {set(duplicates)}")
            return manifest
        except Exception as e:
            if isinstance(e, RulesValidationError):
                raise
            raise RulesValidationError(f"rules.yaml validatsiyadan o'tmadi ({p}): {e}") from e


# --- Car Specifications Schema ---

class DimensionsMeters(BaseModel):
    length: float = Field(..., gt=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    wheelbase: float = Field(..., gt=0)
    front_overhang: float = Field(..., ge=0)
    rear_overhang: float = Field(..., ge=0)


class CarConfig(BaseModel):
    car_id: str = Field(..., min_length=1)
    vin: str = Field(..., min_length=5)
    plate_number: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    manufacture_year: int = Field(..., ge=1990)
    dimensions_meters: DimensionsMeters
    sensor_offsets_meters: dict[str, list[float]]

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> "CarConfig":
        p = Path(path)
        if not p.exists():
            raise ConfigurationError(f"Car config fayli topilmadi: {p.resolve()}")
        try:
            with open(p, encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
            return cls.model_validate(raw_data)
        except Exception as e:
            raise ConfigurationError(f"car.yaml validatsiyadan o'tmadi ({p}): {e}") from e


# --- Calibration Schema ---

class FiducialMark(BaseModel):
    name: str
    expected_px: list[int]
    tolerance_px: int = 15


class CameraCalibration(BaseModel):
    camera_name: Literal["FRONT", "REAR", "LEFT", "RIGHT"]
    resolution: list[int]
    camera_matrix: list[list[float]]
    dist_coeffs: list[float]
    homography_matrix: list[list[float]]
    reference_fiducials: list[FiducialMark] = Field(default_factory=list)
    pixels_per_meter: float = Field(..., gt=0.0)
    last_calibrated_at: str

    @classmethod
    def load_from_json(cls, path: str | Path) -> "CameraCalibration":
        import json
        p = Path(path)
        if not p.exists():
            raise ConfigurationError(f"Kalibrovka fayli topilmadi: {p.resolve()}")
        try:
            with open(p, encoding="utf-8") as f:
                raw_data = json.load(f)
            return cls.model_validate(raw_data)
        except Exception as e:
            raise ConfigurationError(f"Kalibrovka validatsiyadan o'tmadi ({p}): {e}") from e
