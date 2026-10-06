"""ONNX Runtime Object Detection Backend with DirectML, CUDA, and CPU execution providers.

Implements letterbox resizing, normalization, inference execution, and NMS.
Prioritizes DirectML (Windows DirectX 12) for universal GPU acceleration (Intel, AMD, Nvidia),
with CUDA and CPU fallbacks. Completely offline and telemetry-free.
"""

import logging
import time
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

# Standard execution provider priority order
PREFERRED_PROVIDERS_ORDER = [
    "DmlExecutionProvider",       # DirectML: Works on all Windows GPUs (Intel, AMD, Nvidia, Qualcomm)
    "CUDAExecutionProvider",      # Nvidia CUDA
    "TensorrtExecutionProvider",  # Nvidia TensorRT
    "CPUExecutionProvider",       # Portable CPU fallback
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
        provider: str = "auto",
    ):
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.requested_provider = provider

        self._session = None
        self._input_name = ""
        self._output_name = ""
        self.active_provider = "None"
        self.is_gpu_accelerated = False

        self.last_inference_time_ms: float = 0.0
        self.total_latency_ms: float = 0.0
        self.total_inferences: int = 0

        self._init_session(prefer_cuda=prefer_cuda, requested_provider=provider)

    def _init_session(self, prefer_cuda: bool, requested_provider: str) -> None:
        if str(self.model_path) == "mock" or not self.model_path.exists():
            logger.warning(
                "ONNX model fayli diskda topilmadi yoki mock ko'rsatilgan: %s. Fallback rejimida ishlaydi.",
                self.model_path,
            )
            self.active_provider = "Mock/Unavailable"
            return

        try:
            import onnxruntime as ort

            available = ort.get_available_providers()
            candidates = self._resolve_provider_candidates(requested_provider, prefer_cuda, available)

            # Attempt to initialize session trying each provider in order
            for prov in candidates:
                try:
                    providers_to_try = [prov]
                    if prov != "CPUExecutionProvider":
                        providers_to_try.append("CPUExecutionProvider")

                    self._session = ort.InferenceSession(str(self.model_path), providers=providers_to_try)
                    self.active_provider = self._session.get_providers()[0]
                    self.is_gpu_accelerated = "CPU" not in self.active_provider
                    logger.info(
                        "ONNX Runtime modeli muvaffaqiyatli yuklandi: %s | Faol Provider: %s (GPU: %s)",
                        self.model_path,
                        self.active_provider,
                        self.is_gpu_accelerated,
                    )
                    break
                except Exception as ex:
                    logger.warning("Provider %s ishga tushmadi: %s. Navbatdagi provider sinab ko'riladi.", prov, ex)

            if self._session is not None:
                self._input_name = self._session.get_inputs()[0].name
                self._output_name = self._session.get_outputs()[0].name
            else:
                logger.error("Barcha provayderlar xato berdi. Model yuklanmadi.")
        except Exception as e:
            logger.error("ONNX sessiyasini yuklashda kutilmagan xato: %s", e)
            self._session = None
            self.active_provider = "Error"

    def _resolve_provider_candidates(
        self, requested: str, prefer_cuda: bool, available: list[str]
    ) -> list[str]:
        req_lower = requested.lower()
        if req_lower == "dml":
            order = ["DmlExecutionProvider", "CPUExecutionProvider"]
        elif req_lower == "cuda" or prefer_cuda:
            order = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        elif req_lower == "tensorrt":
            order = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
        elif req_lower == "cpu":
            order = ["CPUExecutionProvider"]
        else:  # "auto"
            order = PREFERRED_PROVIDERS_ORDER

        # Filter by available providers, keeping order and ensuring CPU fallback
        matched = [p for p in order if p in available]
        if "CPUExecutionProvider" not in matched:
            matched.append("CPUExecutionProvider")
        return matched

    @property
    def average_latency_ms(self) -> float:
        if self.total_inferences == 0:
            return 0.0
        return self.total_latency_ms / self.total_inferences

    def warmup(self, count: int = 2) -> None:
        """Runs warmup passes to initialize execution buffers and avoid first-frame latency."""
        if self._session is None:
            return
        dummy = np.zeros((1, 3, self.input_size[0], self.input_size[1]), dtype=np.float32)
        for _ in range(count):
            try:
                self._session.run([self._output_name], {self._input_name: dummy})
            except Exception as e:
                logger.warning("Warmup iteratsiyasida ogohlantirish: %s", e)

    def benchmark(self, iterations: int = 15) -> dict[str, float]:
        """Runs benchmark inference passes and returns latency and FPS metrics."""
        if self._session is None:
            return {"avg_latency_ms": 0.0, "min_latency_ms": 0.0, "max_latency_ms": 0.0, "fps": 0.0}

        self.warmup(count=2)
        dummy = np.zeros((1, 3, self.input_size[0], self.input_size[1]), dtype=np.float32)
        times: list[float] = []

        for _ in range(iterations):
            t0 = time.perf_counter()
            self._session.run([self._output_name], {self._input_name: dummy})
            dt_ms = (time.perf_counter() - t0) * 1000.0
            times.append(dt_ms)

        avg_ms = float(np.mean(times))
        min_ms = float(np.min(times))
        max_ms = float(np.max(times))
        fps = 1000.0 / avg_ms if avg_ms > 0 else 0.0

        return {
            "avg_latency_ms": round(avg_ms, 2),
            "min_latency_ms": round(min_ms, 2),
            "max_latency_ms": round(max_ms, 2),
            "fps": round(fps, 1),
        }

    def is_healthy(self) -> bool:
        if self.model_path.exists() and str(self.model_path) != "mock":
            return self._session is not None
        return True

    def _letterbox(self, img: np.ndarray) -> tuple[np.ndarray, float, tuple[float, float]]:
        shape = img.shape[:2]  # h, w
        new_shape = self.input_size
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
        dw = (new_shape[1] - new_unpad[0]) / 2.0
        dh = (new_shape[0] - new_unpad[1]) / 2.0

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return img, r, (dw, dh)

    def detect(self, frame: np.ndarray, camera_name: str, timestamp: float) -> list[Detection]:
        if self._session is None:
            return []

        t_start = time.perf_counter()
        orig_h, orig_w = frame.shape[:2]
        img_boxed, ratio, (dw, dh) = self._letterbox(frame)

        # HWC -> CHW -> NCHW, BGR -> RGB, float32 0..1
        blob = img_boxed[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        blob = np.expand_dims(blob, axis=0)

        # Inference execution
        outputs = self._session.run([self._output_name], {self._input_name: blob})[0]

        # Post-process outputs
        results = self._postprocess(outputs, orig_h, orig_w, ratio, dw, dh, camera_name, timestamp)

        dt_ms = (time.perf_counter() - t_start) * 1000.0
        self.last_inference_time_ms = dt_ms
        self.total_latency_ms += dt_ms
        self.total_inferences += 1

        return results

    def _postprocess(
        self,
        outputs: np.ndarray,
        orig_h: int,
        orig_w: int,
        ratio: float,
        dw: float,
        dh: float,
        camera_name: str,
        timestamp: float,
    ) -> list[Detection]:
        # Handle YOLOv8/v9/v11 [1, features, proposals] or [1, proposals, features]
        arr = np.squeeze(outputs)
        if arr.ndim != 2:
            return []

        expected_v8_features = 4 + len(CLASS_NAMES)  # 12
        expected_v5_features = 5 + len(CLASS_NAMES)  # 13

        if arr.shape[0] in (expected_v8_features, expected_v5_features):
            predictions = arr.T  # [proposals, features]
        elif arr.shape[1] in (expected_v8_features, expected_v5_features):
            predictions = arr  # already [proposals, features]
        elif arr.shape[0] <= 32 and arr.shape[1] > arr.shape[0]:
            predictions = arr.T
        else:
            predictions = arr

        num_features = predictions.shape[1]
        is_yolov5_format = num_features >= 5 + len(CLASS_NAMES)

        boxes: list[list[int]] = []
        confidences: list[float] = []
        class_ids: list[int] = []

        for row in predictions:
            if is_yolov5_format:
                obj_conf = float(row[4])
                scores = row[5:] * obj_conf
            else:
                scores = row[4:]

            class_id = int(np.argmax(scores))
            score = float(scores[class_id])

            if score >= self.confidence_threshold:
                cx, cy, w, h = float(row[0]), float(row[1]), float(row[2]), float(row[3])
                # Scale back to original frame
                x1 = (cx - w / 2.0 - dw) / ratio
                y1 = (cy - h / 2.0 - dh) / ratio
                x2 = (cx + w / 2.0 - dw) / ratio
                y2 = (cy + h / 2.0 - dh) / ratio

                # Clip coordinates
                x1 = max(0.0, min(float(orig_w), x1))
                y1 = max(0.0, min(float(orig_h), y1))
                x2 = max(0.0, min(float(orig_w), x2))
                y2 = max(0.0, min(float(orig_h), y2))

                boxes.append([int(x1), int(y1), int(max(0.0, x2 - x1)), int(max(0.0, y2 - y1))])
                confidences.append(score)
                class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.iou_threshold)

        results: list[Detection] = []
        if len(indices) > 0:
            for idx in np.array(indices).flatten():
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
