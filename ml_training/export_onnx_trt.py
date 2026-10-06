"""YOLO Export Script to ONNX (dynamic shapes, simplified) and TensorRT FP16 engine.

Usage:
    python ml_training/export_onnx_trt.py --weights best.pt --format onnx
"""

import argparse


def export_model(weights_path: str, format_target: str = "onnx", imgsz: int = 640) -> None:
    print(f"=== Model Eksport Qilinmoqda: {weights_path} -> {format_target.upper()} ===")

    try:
        from ultralytics import YOLO

        model = YOLO(weights_path)

        if format_target.lower() == "onnx":
            exported_path = model.export(
                format="onnx",
                imgsz=imgsz,
                dynamic=False,
                simplify=True,
                opset=12,
            )
            print(f"ONNX modeli muvaffaqiyatli saqlandi: {exported_path}")
        elif format_target.lower() in ("engine", "tensorrt"):
            exported_path = model.export(
                format="engine",
                imgsz=imgsz,
                half=True,  # FP16 precision for max speed on Orin
                device="0",
            )
            print(f"TensorRT dvigateli muvaffaqiyatli saqlandi: {exported_path}")
        else:
            raise ValueError(f"Noma'lum format: {format_target}")

    except ImportError:
        print("Ultralytics moduli o'rnatilmagan: pip install ultralytics onnx onnxsim")
    except Exception as e:
        print(f"Eksport xatosi: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO to ONNX / TensorRT Exporter")
    parser.add_argument("--weights", required=True, help="Path to trained .pt file")
    parser.add_argument("--format", default="onnx", choices=["onnx", "engine"])
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    export_model(args.weights, args.format, args.imgsz)
