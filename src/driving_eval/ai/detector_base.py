"""Base classes and data contracts for object detection in the driving evaluation system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def bottom_center(self) -> tuple[float, float]:
        """Contact point on the ground plane (bottom edge center)."""
        return ((self.x1 + self.x2) / 2.0, self.y2)


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: BoundingBox
    camera: str
    timestamp: float
    track_id: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class BaseDetector(ABC):
    """Abstract interface for all AI perception detectors."""

    @abstractmethod
    def detect(self, frame: np.ndarray, camera_name: str, timestamp: float) -> list[Detection]:
        """Runs detection on an image frame and returns list of Detections."""

    @abstractmethod
    def is_healthy(self) -> bool:
        """Returns True if the backend is initialized and responding."""
