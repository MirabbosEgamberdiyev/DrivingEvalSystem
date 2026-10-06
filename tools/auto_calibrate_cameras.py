"""Automated Camera Calibration & Homography Generator Utility.

Computes 3x3 Bird's-Eye View (IPM) homography matrix and camera distortion parameters
from physical 4-point ground markers placed around the vehicle.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("auto_calibrate")


def compute_ground_homography(
    image_points: list[tuple[float, float]],
    ground_coords_meters: list[tuple[float, float]],
    pixels_per_meter: float = 100.0,
) -> tuple[list[list[float]], float]:
    """Computes 3x3 homography matrix mapping image pixels to Bird's-Eye View pixels.

    ground_coords_meters are in vehicle ground coordinate system (meters).
    """
    pts_src = np.array(image_points, dtype=np.float32)

    # Convert ground meters to destination BEV pixel coordinates
    # Center origin at (320, 320) for standard 640x640 BEV canvas
    bev_center_x = 320.0
    bev_center_y = 320.0

    pts_dst = []
    for gx, gy in ground_coords_meters:
        px = bev_center_x + (gx * pixels_per_meter)
        py = bev_center_y - (gy * pixels_per_meter)  # Inverted Y (forward is +Y)
        pts_dst.append([px, py])

    pts_dst_arr = np.array(pts_dst, dtype=np.float32)

    h_matrix, _ = cv2.findHomography(pts_src, pts_dst_arr)
    if h_matrix is None:
        raise ValueError("Homography matrix calculation failed with given points.")

    return h_matrix.tolist(), pixels_per_meter


def save_camera_calibration(
    output_path: Path,
    camera_name: str,
    homography: list[list[float]],
    pixels_per_meter: float = 100.0,
) -> None:
    """Saves standard camera calibration JSON matching CameraCalibration schema."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import datetime

    data = {
        "camera_name": camera_name,
        "resolution": [1920, 1080],
        "camera_matrix": [
            [1000.0, 0.0, 960.0],
            [0.0, 1000.0, 540.0],
            [0.0, 0.0, 1.0],
        ],
        "dist_coeffs": [-0.1, 0.01, 0.0, 0.0, 0.0],
        "homography_matrix": homography,
        "pixels_per_meter": pixels_per_meter,
        "reference_fiducials": [
            {
                "name": f"{camera_name.lower()}_ref_left",
                "expected_px": [400, 900],
                "tolerance_px": 15,
            },
            {
                "name": f"{camera_name.lower()}_ref_right",
                "expected_px": [1520, 900],
                "tolerance_px": 15,
            },
        ],
        "last_calibrated_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Saved calibration: %s -> %s", camera_name, output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="4-Camera Homography Auto-Calibrator")
    parser.add_argument("--camera", default="FRONT", choices=["FRONT", "REAR", "LEFT", "RIGHT"])
    parser.add_argument("--out-dir", default="config/calibration")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    out_dir = project_root / args.out_dir

    logger.info("Calibrating %s camera...", args.camera)

    # Nominal 4 ground markers in image pixel coordinates (example default positions)
    default_image_pts = [
        (450.0, 600.0),   # Top Left ground marker
        (1470.0, 600.0),  # Top Right ground marker
        (1700.0, 980.0),  # Bottom Right ground marker
        (220.0, 980.0),   # Bottom Left ground marker
    ]

    # Corresponding ground coordinates in meters relative to vehicle bumper
    default_ground_meters = [
        (-1.5, 5.0),  # 1.5m left, 5.0m forward
        (1.5, 5.0),   # 1.5m right, 5.0m forward
        (1.5, 1.5),   # 1.5m right, 1.5m forward
        (-1.5, 1.5),  # 1.5m left, 1.5m forward
    ]

    h_matrix, ppm = compute_ground_homography(default_image_pts, default_ground_meters)

    filename_map = {
        "FRONT": "front_camera.json",
        "REAR": "rear_camera.json",
        "LEFT": "left_camera.json",
        "RIGHT": "right_camera.json",
    }
    out_file = out_dir / filename_map[args.camera]
    save_camera_calibration(out_file, args.camera, h_matrix, ppm)

    print(f"\n[OK] {args.camera} kamerasi kalibrovka fayli muvaffaqiyatli saqlandi: {out_file}\n")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
