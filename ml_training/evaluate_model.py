"""Model Evaluation Script: Computes per-class Precision, Recall, mAP50, and mAP50-95."""

import argparse
from pathlib import Path


def evaluate_model(weights_path: str, data_yaml: str) -> None:
    print(f"=== Model Baholash (Evaluation) Boshlanmoqda ===")
    print(f"Model: {weights_path}")
    print(f"Test Dataset: {data_yaml}")

    try:
        from ultralytics import YOLO

        model = YOLO(weights_path)
        metrics = model.val(data=data_yaml, split="test")

        print("\n=== YAKUNIY ANIQLLIK HISOBOTI (PER-CLASS METRICS) ===")
        print(f"{'Sinf Nomi':<20} | {'Precision':<10} | {'Recall':<10} | {'mAP50':<10}")
        print("-" * 60)

        names = metrics.names
        for class_idx, name in names.items():
            # Extract per-class metric values
            try:
                p = metrics.box.p[class_idx]
                r = metrics.box.r[class_idx]
                map50 = metrics.box.ap50[class_idx]
                print(f"{name:<20} | {p:<10.3f} | {r:<10.3f} | {map50:<10.3f}")
            except Exception:
                print(f"{name:<20} | N/A        | N/A        | N/A")

        print("-" * 60)
        print(f"Umumiy Precision: {metrics.box.mp:.3f}")
        print(f"Umumiy Recall:    {metrics.box.mr:.3f}")
        print(f"Umumiy mAP50:     {metrics.box.map50:.3f}")
        print(f"Umumiy mAP50-95:  {metrics.box.map:.3f}")

    except ImportError:
        print("Ultralytics moduli o'rnatilmagan: pip install ultralytics")
    except Exception as e:
        print(f"Baholash paytida xato: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Model Evaluation Script")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", default="dataset.yaml")
    args = parser.parse_args()

    evaluate_model(args.weights, args.data)
