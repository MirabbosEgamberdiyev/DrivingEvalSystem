"""Base class and context definitions for rule engine plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from driving_eval.ai.detector_base import Detection
from driving_eval.hardware.calibration import CalibrationService
from driving_eval.hardware.camera_service import FrameBundle
from driving_eval.hardware.sensor_fusion import FusedVehicleState


@dataclass
class EvaluationContext:
    timestamp: float
    current_exercise: str
    vehicle_state: FusedVehicleState
    detections: list[Detection]
    frame_bundle: FrameBundle | None
    calibrations: dict[str, CalibrationService]


@dataclass
class RuleEvaluationResult:
    violated: bool
    is_suspect: bool = False
    confidence: float = 0.0
    camera: str = "FRONT"
    track_id: int | None = None
    details: str = ""
    evidence_metadata: dict[str, Any] = field(default_factory=dict)


class BaseRulePlugin(ABC):
    """Abstract interface for modular rule evaluation plugins."""

    @property
    @abstractmethod
    def rule_code(self) -> str:
        """Unique rule code matching config/rules.yaml (e.g. CONE_TOUCH)."""

    @abstractmethod
    def evaluate(self, ctx: EvaluationContext) -> RuleEvaluationResult:
        """Evaluates vehicle telemetry and camera perceptions against this specific rule."""
