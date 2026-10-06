"""Unit tests for ONNXDetector and YOLO-to-ONNX export utility."""

import tempfile
from pathlib import Path

import numpy as np

from driving_eval.ai.onnx_detector import ONNXDetector
from scripts.export_yolo_to_onnx import (
    benchmark_model,
    export_model,
    validate_model,
)


def test_onnx_detector_initialization_mock_and_fallback():
    # 1. Mock path
    detector = ONNXDetector(model_path="mock", confidence_threshold=0.75)
    assert detector.is_healthy() is True
    assert detector.active_provider == "Mock/Unavailable"
    assert detector.average_latency_ms == 0.0

    # Detect on empty or mock should return empty list gracefully
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    dets = detector.detect(dummy_frame, "FRONT", 10.0)
    assert dets == []

    # Warmup and benchmark on mock
    detector.warmup(count=1)
    bench = detector.benchmark(iterations=5)
    assert "avg_latency_ms" in bench
    assert bench["fps"] == 0.0

    # 2. Nonexistent path
    detector_missing = ONNXDetector(model_path="nonexistent_model.onnx")
    assert detector_missing.is_healthy() is True
    assert detector_missing.active_provider == "Mock/Unavailable"


def test_onnx_detector_provider_candidate_resolution():
    detector = ONNXDetector(model_path="mock")
    all_mock_providers = ["DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]

    # Auto resolution prioritizes DirectML first on Windows
    auto_candidates = detector._resolve_provider_candidates("auto", False, all_mock_providers)
    assert auto_candidates[0] == "DmlExecutionProvider"
    assert "CPUExecutionProvider" in auto_candidates

    # DML request
    dml_candidates = detector._resolve_provider_candidates("dml", False, all_mock_providers)
    assert dml_candidates == ["DmlExecutionProvider", "CPUExecutionProvider"]

    # CUDA request
    cuda_candidates = detector._resolve_provider_candidates("cuda", False, all_mock_providers)
    assert cuda_candidates == ["CUDAExecutionProvider", "CPUExecutionProvider"]

    # CPU request
    cpu_candidates = detector._resolve_provider_candidates("cpu", False, all_mock_providers)
    assert cpu_candidates == ["CPUExecutionProvider"]


def test_onnx_detector_letterbox():
    detector = ONNXDetector(model_path="mock", input_size=(640, 640))
    img = np.zeros((720, 1280, 3), dtype=np.uint8)

    boxed, ratio, (dw, dh) = detector._letterbox(img)
    assert boxed.shape == (640, 640, 3)
    assert ratio == 640.0 / 1280.0  # 0.5
    assert dw == 0.0
    assert dh == (640 - 720 * 0.5) / 2.0  # 140.0


def test_onnx_detector_postprocessing_yolov8_and_yolov5():
    detector = ONNXDetector(model_path="mock", confidence_threshold=0.70)

    # 1. YOLOv8 format: [1, 12, 10] (4 coords + 8 classes = 12 channels)
    num_classes = 8
    num_proposals = 10
    raw_v8 = np.zeros((1, 4 + num_classes, num_proposals), dtype=np.float32)

    # Set proposal 0 to cone (index 0 in classes) with high confidence 0.95
    # bbox in 640x640: cx=320, cy=320, w=100, h=100
    raw_v8[0, 0, 0] = 320.0
    raw_v8[0, 1, 0] = 320.0
    raw_v8[0, 2, 0] = 100.0
    raw_v8[0, 3, 0] = 100.0
    raw_v8[0, 4, 0] = 0.95  # cone score

    results_v8 = detector._postprocess(
        outputs=raw_v8,
        orig_h=720,
        orig_w=1280,
        ratio=0.5,
        dw=0.0,
        dh=140.0,
        camera_name="FRONT",
        timestamp=25.0,
    )

    assert len(results_v8) == 1
    det = results_v8[0]
    assert det.label == "cone"
    assert round(det.confidence, 2) == 0.95
    assert det.camera == "FRONT"
    assert det.timestamp == 25.0
    # Scaled back coords: cx=(320 - 0)/0.5 = 640, cy=(320 - 140)/0.5 = 360
    assert 530 <= det.bbox.x1 <= 550
    assert 250 <= det.bbox.y1 <= 270

    # 2. YOLOv5 format: [1, 10, 13] (cx, cy, w, h, obj_conf, 8 classes = 13 channels)
    raw_v5 = np.zeros((1, num_proposals, 5 + num_classes), dtype=np.float32)
    raw_v5[0, 1, 0] = 320.0  # cx
    raw_v5[0, 1, 1] = 320.0  # cy
    raw_v5[0, 1, 2] = 80.0   # w
    raw_v5[0, 1, 3] = 80.0   # h
    raw_v5[0, 1, 4] = 1.0    # obj conf
    raw_v5[0, 1, 6] = 0.90   # stop_line (class 1)

    results_v5 = detector._postprocess(
        outputs=raw_v5,
        orig_h=720,
        orig_w=1280,
        ratio=0.5,
        dw=0.0,
        dh=140.0,
        camera_name="FRONT",
        timestamp=26.0,
    )
    assert len(results_v5) == 1
    assert results_v5[0].label == "stop_line"
    assert round(results_v5[0].confidence, 2) == 0.90


def test_export_yolo_to_onnx_utility():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        weights_file = tmp_path / "driving_yolo.pt"
        onnx_file = tmp_path / "driving_yolo.onnx"

        # Test synthetic export
        success = export_model(weights_path=weights_file, output_path=onnx_file, imgsz=640, opset=17)
        assert success is True
        assert onnx_file.exists()
        assert onnx_file.stat().st_size > 0

        # Test model validation
        val_res = validate_model(onnx_file, imgsz=640)
        assert val_res.get("valid") is True

        # Test benchmark
        bench_res = benchmark_model(onnx_file, iterations=5)
        assert "avg_latency_ms" in bench_res
        assert bench_res["fps"] > 0
