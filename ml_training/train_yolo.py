"""YOLO model training script for driving evaluation autodrome dataset.

Usage:
    python ml_training/train_yolo.py --data dataset.yaml --epochs 100 --batch 32
"""

import argparse


def train_yolo(
    data_yaml: str,
    epochs: int = 100,
    batch_size: int = 32,
    img_size: int = 640,
    model_name: str = "yolov8m.pt",
    output_dir: str = "runs/train",
) -> None:
    print("=== YOLO O'qitish Boshlanmoqda ===")
    print(f"Dataset config: {data_yaml}")
    print(f"Baza model: {model_name}")
    print(f"Epochlar: {epochs}, Batch: {batch_size}, Input: {img_size}")

    try:
        from ultralytics import YOLO

        model = YOLO(model_name)
        model.train(
            data=data_yaml,
            epochs=epochs,
            batch=batch_size,
            imgsz=img_size,
            project=output_dir,
            name="driving_eval_yolo",
            device="0",  # GPU 0
            workers=8,
            optimizer="AdamW",
            lr0=0.001,
            augment=True,
            hsv_h=0.015,
            hsv_s=0.7,
            hsv_v=0.4,
            mosaic=1.0,
            mixup=0.1,
        )
        print("Model o'qitish muvaffaqiyatli yakunlandi!")
    except ImportError:
        print("Ultralytics paketi topilmadi. O'rnatish: pip install ultralytics")
    except Exception as e:
        print(f"O'qitish jarayonida xato: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO Training Script")
    parser.add_argument("--data", default="dataset.yaml", help="Path to dataset.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--model", default="yolov8m.pt")
    args = parser.parse_args()

    train_yolo(args.data, args.epochs, args.batch, args.imgsz, args.model)
