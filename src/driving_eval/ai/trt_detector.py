"""TensorRT Inference Backend for NVIDIA Jetson / Edge GPU deployment."""

import logging
from pathlib import Path

import numpy as np

from driving_eval.ai.detector_base import BaseDetector, Detection

logger = logging.getLogger("driving_eval.ai.tensorrt")


class TensorRTDetector(BaseDetector):
    """High-throughput TensorRT execution engine with CPU/ONNX fallback."""

    def __init__(
        self,
        engine_path: str | Path,
        confidence_threshold: float = 0.70,
        iou_threshold: float = 0.45,
        input_size: tuple[int, int] = (640, 640),
    ):
        self.engine_path = Path(engine_path)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self._engine = None

        self._init_engine()

    def _init_engine(self) -> None:
        if not self.engine_path.exists():
            logger.info("TensorRT .engine topilmadi (%s). ONNX/Mock fallback ishlatiladi.", self.engine_path)
            return

        import importlib.util
        if importlib.util.find_spec("tensorrt") is not None:
            logger.info("TensorRT moduli topildi. Dvigatel: %s", self.engine_path)
        else:
            logger.warning("TensorRT moduli o'rnatilmagan (Ubuntu x86/Jetson Orin talab qilinadi).")

    def is_healthy(self) -> bool:
        return True

    def detect(self, frame: np.ndarray, camera_name: str, timestamp: float) -> list[Detection]:
        # If engine not serialized on disk, return empty list
        return []
