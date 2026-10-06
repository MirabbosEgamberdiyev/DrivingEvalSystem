"""Deterministic mock detector for offline testing without requiring trained model weights.

Enables full pipeline testing, unit tests, and CI/CD without hardware dependencies.
"""

from collections.abc import Callable

import numpy as np

from driving_eval.ai.detector_base import BaseDetector, Detection


class MockDetector(BaseDetector):
    """Scriptable mock detector for simulation and testing."""

    def __init__(self, healthy: bool = True):
        self._healthy = healthy
        self._scheduled_detections: list[Detection] = []
        self._step_counter: int = 0
        self._scripted_provider: Callable[[int, str, float], list[Detection]] | None = None

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy

    def schedule_detection(self, detection: Detection) -> None:
        """Schedules a detection to be emitted on next call matching camera."""
        self._scheduled_detections.append(detection)

    def set_scripted_provider(self, provider: Callable[[int, str, float], list[Detection]]) -> None:
        """Sets a callable: provider(step, camera_name, timestamp) -> list[Detection]."""
        self._scripted_provider = provider

    def detect(self, frame: np.ndarray, camera_name: str, timestamp: float) -> list[Detection]:
        if not self._healthy:
            raise RuntimeError("MockDetector nosoz holatda chaqirildi!")

        self._step_counter += 1

        if self._scripted_provider:
            return self._scripted_provider(self._step_counter, camera_name, timestamp)

        # Return matching scheduled detections and pop them
        matching = []
        remaining = []
        for det in self._scheduled_detections:
            if det.camera == camera_name:
                matching.append(det)
            else:
                remaining.append(det)
        self._scheduled_detections = remaining
        return matching

    def is_healthy(self) -> bool:
        return self._healthy
