"""Camera calibration, undistortion, Bird's-Eye View (IPM), and fiducial drift verification."""

import math
from collections.abc import Sequence
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
        self.inv_homography = np.linalg.inv(self.homography)
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

    def generate_bev_image(
        self, frame: np.ndarray, output_size: tuple[int, int] = (640, 640)
    ) -> np.ndarray:
        """Generates Bird's-Eye View (Inverse Perspective Mapping) image."""
        undistorted = self.undistort_frame(frame)
        bev = cv2.warpPerspective(undistorted, self.homography, output_size)
        return bev

    def pixel_to_ground_plane(self, px: float, py: float) -> tuple[float, float]:
        """Maps pixel coordinate (px, py) to bird's-eye ground coordinate in meters."""
        pt = np.array([[[px, py]]], dtype=np.float32)
        warped = cv2.perspectiveTransform(pt, self.homography)
        wx = float(warped[0][0][0]) / self.pixels_per_meter
        wy = float(warped[0][0][1]) / self.pixels_per_meter
        return (wx, wy)

    def ground_to_pixel(self, gx: float, gy: float) -> tuple[float, float]:
        """Maps ground coordinate (gx, gy) in meters back to camera image pixel (px, py)."""
        wx = gx * self.pixels_per_meter
        wy = gy * self.pixels_per_meter
        pt = np.array([[[wx, wy]]], dtype=np.float32)
        unwarped = cv2.perspectiveTransform(pt, self.inv_homography)
        px = float(unwarped[0][0][0])
        py = float(unwarped[0][0][1])
        return (px, py)

    def project_polygon_to_ground(
        self, points_px: Sequence[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """Converts pixel polygon vertices into ground plane coordinates in meters."""
        return [self.pixel_to_ground_plane(px, py) for px, py in points_px]

    def compute_distance_meters(
        self, pt1_px: tuple[float, float], pt2_px: tuple[float, float]
    ) -> float:
        """Computes Euclidean ground distance in meters between two image points."""
        gx1, gy1 = self.pixel_to_ground_plane(pt1_px[0], pt1_px[1])
        gx2, gy2 = self.pixel_to_ground_plane(pt2_px[0], pt2_px[1])
        return math.hypot(gx2 - gx1, gy2 - gy1)

    def point_to_line_distance_ground(
        self,
        point_g: tuple[float, float],
        line_start_g: tuple[float, float],
        line_end_g: tuple[float, float],
    ) -> float:
        """Calculates minimum distance from a ground point to a ground line segment in meters."""
        px, py = point_g
        x1, y1 = line_start_g
        x2, y2 = line_end_g

        dx = x2 - x1
        dy = y2 - y1
        line_len_sq = dx * dx + dy * dy

        if line_len_sq < 1e-6:
            return math.hypot(px - x1, py - y1)

        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / line_len_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

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

    def detect_fiducials_and_verify(
        self, frame: np.ndarray, search_window_px: int = 30
    ) -> tuple[bool, float, list[str]]:
        """Automated image-based fiducial verification on frame corners."""
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        detected: dict[str, tuple[int, int]] = {}
        for fid in self.calib.reference_fiducials:
            exp_x, exp_y = fid.expected_px
            x1 = max(0, exp_x - search_window_px)
            y1 = max(0, exp_y - search_window_px)
            x2 = min(w, exp_x + search_window_px)
            y2 = min(h, exp_y + search_window_px)

            roi = gray[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            # Detect prominent corner in ROI
            corners = cv2.goodFeaturesToTrack(roi, maxCorners=1, qualityLevel=0.05, minDistance=5)
            if corners is not None and len(corners) > 0:
                cx, cy = corners[0][0]
                detected[fid.name] = (int(x1 + cx), int(y1 + cy))
            else:
                # Fallback to expected if no corner found
                detected[fid.name] = (exp_x, exp_y)

        return self.verify_fiducial_drift(detected)


class MultiCameraCalibration:
    """Loads and aggregates calibrations for all 4 vehicle cameras."""

    def __init__(self, calibrations: dict[str, CalibrationService]):
        self._calibrations = calibrations

    @classmethod
    def load_from_dir(cls, directory: str | Path) -> "MultiCameraCalibration":
        p = Path(directory)
        cals: dict[str, CalibrationService] = {}
        cam_files = {
            "FRONT": "front_camera.json",
            "REAR": "rear_camera.json",
            "LEFT": "left_camera.json",
            "RIGHT": "right_camera.json",
        }
        for cam_name, fname in cam_files.items():
            fpath = p / fname
            if fpath.exists():
                cals[cam_name] = CalibrationService.load(fpath)
        return cls(cals)

    def get_calibration(self, camera_name: str) -> CalibrationService | None:
        return self._calibrations.get(camera_name)

    def verify_all_cameras_drift(
        self, frames_by_camera: dict[str, np.ndarray]
    ) -> tuple[bool, dict[str, list[str]]]:
        all_passed = True
        all_details: dict[str, list[str]] = {}

        for cam_name, cal in self._calibrations.items():
            frame = frames_by_camera.get(cam_name)
            if frame is not None:
                passed, _, details = cal.detect_fiducials_and_verify(frame)
                if not passed:
                    all_passed = False
                    all_details[cam_name] = details

        return all_passed, all_details
