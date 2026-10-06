"""Core domain exceptions for Driving Evaluation System.

All operational errors are strongly typed to prevent silent failures.
"""


class DrivingEvalError(Exception):
    """Base exception for all domain errors."""


class ConfigurationError(DrivingEvalError):
    """Raised when configuration validation fails."""


class RulesValidationError(DrivingEvalError):
    """Raised when rules.yaml is invalid or schema check fails."""


class InvalidStateTransitionError(DrivingEvalError):
    """Raised when an illegal state machine transition is attempted."""

    def __init__(self, current_state: str, target_state: str, reason: str = ""):
        message = f"Illegal state transition: '{current_state}' -> '{target_state}'."
        if reason:
            message += f" Sabab: {reason}"
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state
        self.reason = reason


class PrecheckFailureError(DrivingEvalError):
    """Raised when one or more mandatory pre-checks fail before test start."""

    def __init__(self, component: str, reason: str):
        super().__init__(f"Pre-check muvaffaqiyatsiz bo'ldi [{component}]: {reason}")
        self.component = component
        self.reason = reason


class CalibrationDriftError(PrecheckFailureError):
    """Raised when camera calibration fiducial points drift beyond allowed threshold."""

    def __init__(self, camera_name: str, drift_px: float, max_allowed_px: float):
        reason = f"Siljish {drift_px:.2f}px ruxsat etilgan {max_allowed_px:.2f}px dan katta"
        super().__init__(f"CALIBRATION_{camera_name}", reason)
        self.camera_name = camera_name
        self.drift_px = drift_px
        self.max_allowed_px = max_allowed_px


class CameraStreamError(DrivingEvalError):
    """Raised when camera connection, sync, or FPS fails."""


class StorageCapacityError(DrivingEvalError):
    """Raised when available storage is below the mandatory safety threshold."""


class CriticalViolationError(DrivingEvalError):
    """Raised when a critical violation occurs during active test."""

    def __init__(self, rule_code: str, description: str):
        super().__init__(f"Kritik qoidabuzarlik: [{rule_code}] {description}")
        self.rule_code = rule_code
        self.description = description
