"""ONNX Runtime Object Detection Backend.

Implements letterbox resizing, normalization, inference execution, and NMS.
Works completely offline without external network or telemetry calls.
"""

import logging
from pathlib import Path

import cv2
import numpy as np

from driving_eval.ai.detector_base import BaseDetector, BoundingBox, Detection

logger = logging.getLogger("driving_eval.ai.onnx")

CLASS_NAMES = [
    "cone",
    "stop_line",
    "solid_line",
    "dashed_line",
    "vehicle",
    "pedestrian",
    "barrier",
    "curb",
]


class ONNXDetector(BaseDetector):
    """Production detector loading exported ONNX models via onnxruntime."""

    def __init__(
        self,
        model_path: str | Path,
        confidence_threshold: float = 0.70,
        iou_threshold: float = 0.45,
        input_size: tuple[int, int] = (640, 640),
        prefer_cuda: bool = False,
    ):
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self._session = None
        self._input_name = ""
        self._output_name = ""

        self._init_session(prefer_cuda)

    def _init_session(self, prefer_cuda: bool) -> None:
        if not self.model_path.exists():
            logger.warning(
                "ONNX model fayli diskda topilmadi: %s. Mock/Fallback rejimida ishlaydi.",
                self.model_path,
            )
            return

        try:
            import onnxruntime as ort

            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if prefer_cuda else ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(str(self.model_path), providers=providers)
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            logger.info("ONNX Runtime modeli yuklandi: %s (%s)", self.model_path, providers[0])
        except Exception as e:
            logger.error("ONNX sessiyasini yuklashda xato: %s", e)
            self._session = None

    def is_healthy(self) -> bool:
        # If model exists on disk, session must be valid; otherwise healthy in mock fallback
        if self.model_path.exists():
            return self._session is not None
        return True

    def _letterbox(self, img: np.ndarray) -> tuple[np.ndarray, float, tuple[float, float]]:
        shape = img.shape[:2]  # h, w
        new_shape = self.input_size
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
        dw = (new_shape[1] - new_unpad[0]) / 2
        dh = (new_shape[0] - new_unpad[1]) / 2

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return img, r, (dw, dh)

    def detect(self, frame: np.ndarray, camera_name: str, timestamp: float) -> list[Detection]:
        if self._session is None:
            # Standalone fallback: return empty detections if model weights are not loaded yet
            return []

        orig_h, orig_w = frame.shape[:2]
        img_boxed, ratio, (dw, dh) = self._letterbox(frame)

        # HWC -> CHW -> NCHW, BGR -> RGB, float32 0..1
        blob = img_boxed[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        blob = np.expand_dims(blob, axis=0)

        # Inference
        outputs = self._session.run([self._output_name], {self._input_name: blob})[0]

        # Post-process YOLO outputs (shape: [1, num_classes + 4, num_proposals])
        predictions = np.squeeze(outputs).T

        boxes = []
        confidences = []
        class_ids = []

        for row in predictions:
            scores = row[4:]
            class_id = int(np.argmax(scores))
            score = float(scores[class_id])
            if score >= self.confidence_threshold:
                cx, cy, w, h = row[0], row[1], row[2], row[3]
                # Scale back to original frame
                x1 = (cx - w / 2 - dw) / ratio
                y1 = (cy - h / 2 - dh) / ratio
                x2 = (cx + w / 2 - dw) / ratio
                y2 = (cy + h / 2 - dh) / ratio

                boxes.append([int(x1), int(y1), int(max(0, x2 - x1)), int(max(0, y2 - y1))])
                confidences.append(score)
                class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.iou_threshold)

        results = []
        if len(indices) > 0:
            for idx in indices.flatten():
                b = boxes[idx]
                cid = class_ids[idx]
                label = CLASS_NAMES[cid] if cid < len(CLASS_NAMES) else f"cls_{cid}"
                results.append(
                    Detection(
                        label=label,
                        confidence=confidences[idx],
                        bbox=BoundingBox(
                            x1=float(b[0]),
                            y1=float(b[1]),
                            x2=float(b[0] + b[2]),
                            y2=float(b[1] + b[3]),
                        ),
                        camera=camera_name,
                        timestamp=timestamp,
                    )
                )

        return results
