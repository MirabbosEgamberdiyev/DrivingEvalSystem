"""Camera calibration, undistortion, Bird's-Eye View (IPM), and fiducial drift verification."""

import math
from pathlib import Path

import cv2
import numpy as np

from driving_eval.core.config_schema import CameraCalibration


class CalibrationService:
    """Handles intrinsic/extrinsic transformations and calibration integrity checks."""

    def __init__(self, calibration_data: CameraCalibration):
        self.calib = calibration_data
        self.camera_matrix = np.array(self.calib.camera_matrix, dtype=np.float64)
        self.dist_coeffs = np.array(self.calib.dist_coeffs, dtype=np.float64)
        self.homography = np.array(self.calib.homography_matrix, dtype=np.float64)
        self.pixels_per_meter = self.calib.pixels_per_meter

    @classmethod
    def load(cls, json_path: str | Path) -> "CalibrationService":
        data = CameraCalibration.load_from_json(json_path)
        return cls(data)

    def undistort_frame(self, frame: np.ndarray) -> np.ndarray:
        """Removes fisheye/lens distortion."""
        h, w = frame.shape[:2]
        new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), 1, (w, h)
        )
        return cv2.undistort(frame, self.camera_matrix, self.dist_coeffs, None, new_camera_matrix)

    def pixel_to_ground_plane(self, px: float, py: float) -> tuple[float, float]:
        """Maps pixel coordinate (px, py) to bird's-eye ground coordinate in meters."""
        pt = np.array([[[px, py]]], dtype=np.float32)
        warped = cv2.perspectiveTransform(pt, self.homography)
        wx = float(warped[0][0][0]) / self.pixels_per_meter
        wy = float(warped[0][0][1]) / self.pixels_per_meter
        return (wx, wy)

    def compute_distance_meters(self, pt1_px: tuple[float, float], pt2_px: tuple[float, float]) -> float:
        """Computes Euclidean ground distance in meters between two image points."""
        gx1, gy1 = self.pixel_to_ground_plane(pt1_px[0], pt1_px[1])
        gx2, gy2 = self.pixel_to_ground_plane(pt2_px[0], pt2_px[1])
        return math.hypot(gx2 - gx1, gy2 - gy1)

    def verify_fiducial_drift(
        self,
        detected_fiducials: dict[str, tuple[int, int]],
        max_drift_threshold_px: float = 15.0,
    ) -> tuple[bool, float, list[str]]:
        """Verifies if reference fiducial markers (e.g. hood corners, mirror base) have shifted.

        Returns: (passed, max_observed_drift, drift_details)
        """
        max_drift = 0.0
        details = []
        for fid in self.calib.reference_fiducials:
            if fid.name in detected_fiducials:
                detected_x, detected_y = detected_fiducials[fid.name]
                exp_x, exp_y = fid.expected_px
                drift = math.hypot(detected_x - exp_x, detected_y - exp_y)
                if drift > max_drift:
                    max_drift = drift

                allowed = min(fid.tolerance_px, max_drift_threshold_px)
                if drift > allowed:
                    details.append(
                        f"Fiducial '{fid.name}' siljishi {drift:.2f}px (ruxsat: {allowed:.2f}px)"
                    )

        passed = len(details) == 0
        return passed, max_drift, details
