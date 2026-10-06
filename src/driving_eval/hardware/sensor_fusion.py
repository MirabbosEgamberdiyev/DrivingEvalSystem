"""Sensor fusion combining GPS, IMU, OBD-II, and camera Visual Odometry.

Produces robust vehicle state estimation (speed, position, slope, seatbelt, signals, rollback),
with Dead Reckoning fallback when GPS/OBD signals drop out in tunnels or shaded zones.
"""

import math
import time
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class GPSData:
    lat: float
    lon: float
    speed_kmh: float
    heading_deg: float
    fix_valid: bool
    timestamp: float


@dataclass
class IMUData:
    accel_x: float  # Lateral
    accel_y: float  # Longitudinal (forward/back)
    accel_z: float  # Vertical
    pitch_deg: float  # Slope inclination
    roll_deg: float
    yaw_rate: float
    timestamp: float


@dataclass
class OBDData:
    speed_kmh: float
    engine_rpm: int
    seatbelt_fastened: bool
    handbrake_active: bool
    turn_signal_left: bool
    turn_signal_right: bool
    timestamp: float


@dataclass
class VisualOdometryData:
    speed_kmh: float
    displacement_m: float
    dx_m: float
    dy_m: float
    quality: float
    timestamp: float


@dataclass
class FusedVehicleState:
    timestamp: float
    speed_kmh: float
    is_stopped: bool
    pitch_deg: float
    seatbelt_fastened: bool
    handbrake_active: bool
    turn_signal_active: bool  # Either left or right
    lat: float
    lon: float
    rollback_distance_meters: float
    source_quality: str
    standstill_confidence: float = 1.0


class VisualOdometryEstimator:
    """Estimates forward displacement and ground speed from optical flow on road surface."""

    def __init__(self, pixels_per_meter: float = 42.5):
        self.pixels_per_meter = pixels_per_meter
        self._prev_gray: np.ndarray | None = None
        self._prev_pts: np.ndarray | None = None
        self._last_timestamp: float | None = None

    def estimate_motion(
        self, frame: np.ndarray, timestamp: float
    ) -> VisualOdometryData:
        """Estimates frame-to-frame vehicle translation and forward speed."""
        h, w = frame.shape[:2]
        # Road surface region of interest (lower half of front camera)
        roi_y1 = int(h * 0.55)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        road_roi = gray[roi_y1:h, :]

        dt = (timestamp - self._last_timestamp) if self._last_timestamp is not None else 0.033
        self._last_timestamp = timestamp
        dt = max(0.005, dt)

        if self._prev_gray is None:
            self._prev_gray = road_roi
            self._prev_pts = cv2.goodFeaturesToTrack(
                road_roi, maxCorners=100, qualityLevel=0.03, minDistance=10
            )
            return VisualOdometryData(
                speed_kmh=0.0,
                displacement_m=0.0,
                dx_m=0.0,
                dy_m=0.0,
                quality=1.0,
                timestamp=timestamp,
            )

        if self._prev_pts is None or len(self._prev_pts) < 10:
            self._prev_pts = cv2.goodFeaturesToTrack(
                self._prev_gray, maxCorners=100, qualityLevel=0.03, minDistance=10
            )

        if self._prev_pts is None or len(self._prev_pts) < 5:
            self._prev_gray = road_roi
            return VisualOdometryData(
                speed_kmh=0.0,
                displacement_m=0.0,
                dx_m=0.0,
                dy_m=0.0,
                quality=0.0,
                timestamp=timestamp,
            )

        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(  # type: ignore[call-overload]
            self._prev_gray, road_roi, self._prev_pts, None
        )

        good_prev = self._prev_pts[status == 1]
        good_next = next_pts[status == 1]

        if len(good_next) < 5:
            self._prev_gray = road_roi
            self._prev_pts = None
            return VisualOdometryData(
                speed_kmh=0.0,
                displacement_m=0.0,
                dx_m=0.0,
                dy_m=0.0,
                quality=0.2,
                timestamp=timestamp,
            )

        # Displacements in pixels (flow points move downward as car moves forward)
        diffs = good_next - good_prev
        median_dx_px = float(np.median(diffs[:, 0]))
        median_dy_px = float(np.median(diffs[:, 1]))

        # Ground meters
        dx_m = median_dx_px / self.pixels_per_meter
        dy_m = median_dy_px / self.pixels_per_meter
        dist_m = math.hypot(dx_m, dy_m)

        speed_mps = dist_m / dt
        speed_kmh = speed_mps * 3.6

        self._prev_gray = road_roi
        self._prev_pts = good_next.reshape(-1, 1, 2)

        return VisualOdometryData(
            speed_kmh=round(speed_kmh, 1),
            displacement_m=round(dist_m, 3),
            dx_m=round(dx_m, 3),
            dy_m=round(dy_m, 3),
            quality=min(1.0, len(good_next) / 50.0),
            timestamp=timestamp,
        )

    def simulate_motion(self, speed_kmh: float, dt: float, timestamp: float) -> VisualOdometryData:
        """Simulated Visual Odometry step for headless testing and synthetic replays."""
        speed_mps = speed_kmh / 3.6
        dist_m = speed_mps * dt
        self._last_timestamp = timestamp
        return VisualOdometryData(
            speed_kmh=round(speed_kmh, 1),
            displacement_m=round(dist_m, 3),
            dx_m=0.0,
            dy_m=round(dist_m, 3),
            quality=0.95,
            timestamp=timestamp,
        )


class SensorFusionService:
    """Fuses multi-modal sensor streams into a reliable ground truth state."""

    def __init__(self, speed_stop_threshold_kmh: float = 1.5):
        self.speed_stop_threshold_kmh = speed_stop_threshold_kmh
        self._latest_gps: GPSData | None = None
        self._latest_imu: IMUData | None = None
        self._latest_obd: OBDData | None = None
        self._latest_vo: VisualOdometryData | None = None

        self._accumulated_rollback_m: float = 0.0
        self._last_state_time: float = time.monotonic()

        # Dead Reckoning position estimation (Tashkent Autodrome coordinates by default)
        self._est_lat: float = 41.311081
        self._est_lon: float = 69.240562
        self._est_heading_deg: float = 0.0

    def update_gps(self, data: GPSData) -> None:
        self._latest_gps = data
        if data.fix_valid:
            self._est_lat = data.lat
            self._est_lon = data.lon
            self._est_heading_deg = data.heading_deg

    def update_imu(self, data: IMUData) -> None:
        self._latest_imu = data

    def update_obd(self, data: OBDData) -> None:
        self._latest_obd = data

    def update_visual_odometry(self, data: VisualOdometryData) -> None:
        self._latest_vo = data

    def reset_rollback(self) -> None:
        self._accumulated_rollback_m = 0.0

    def is_rollback_exceeded(self, threshold_meters: float = 0.20) -> bool:
        """Returns True if vehicle rolled back more than threshold (default 20 cm)."""
        return self._accumulated_rollback_m > threshold_meters

    def confirm_vehicle_stopped(self, threshold_kmh: float | None = None) -> bool:
        """Multi-source verification that the vehicle is physically stationary."""
        limit = threshold_kmh or self.speed_stop_threshold_kmh
        agreements = 0
        total_sources = 0

        # Check OBD
        if self._latest_obd and (time.monotonic() - self._latest_obd.timestamp) < 1.0:
            total_sources += 1
            if self._latest_obd.speed_kmh < limit or self._latest_obd.handbrake_active:
                agreements += 1

        # Check GPS
        if self._latest_gps and self._latest_gps.fix_valid and (time.monotonic() - self._latest_gps.timestamp) < 2.0:
            total_sources += 1
            if self._latest_gps.speed_kmh < limit:
                agreements += 1

        # Check IMU
        if self._latest_imu and (time.monotonic() - self._latest_imu.timestamp) < 1.0:
            total_sources += 1
            if abs(self._latest_imu.accel_y) < 0.20 and abs(self._latest_imu.yaw_rate) < 0.5:
                agreements += 1

        # Check Visual Odometry
        if self._latest_vo and (time.monotonic() - self._latest_vo.timestamp) < 1.5:
            total_sources += 1
            if self._latest_vo.speed_kmh < limit:
                agreements += 1

        if total_sources == 0:
            return True
        return (agreements / total_sources) >= 0.5

    def get_fused_state(self, current_timestamp: float) -> FusedVehicleState:
        now = current_timestamp
        dt = max(0.001, now - self._last_state_time)
        self._last_state_time = now

        # -------------------------------------------------------------
        # 1. Speed determination with multi-tiered fallback:
        #    OBD (primary) -> GPS (fallback) -> VO (dead reckoning) -> IMU
        # -------------------------------------------------------------
        if self._latest_obd and (now - self._latest_obd.timestamp) < 1.0:
            speed = max(0.0, self._latest_obd.speed_kmh)
            quality = "OBD_PRIMARY"
        elif self._latest_gps and self._latest_gps.fix_valid and (now - self._latest_gps.timestamp) < 2.0:
            speed = max(0.0, self._latest_gps.speed_kmh)
            quality = "GPS_FALLBACK"
        elif self._latest_vo and (now - self._latest_vo.timestamp) < 2.0 and self._latest_vo.quality > 0.3:
            speed = max(0.0, self._latest_vo.speed_kmh)
            quality = "VO_DEAD_RECKONING"
        elif self._latest_imu and (now - self._latest_imu.timestamp) < 1.0:
            # Estimate roughly from IMU acceleration
            speed = max(0.0, abs(self._latest_imu.accel_y) * dt * 3.6)
            quality = "IMU_DEAD_RECKONING"
        else:
            speed = 0.0
            quality = "DEGRADED_ZERO"

        is_stopped = speed < self.speed_stop_threshold_kmh

        # -------------------------------------------------------------
        # 2. Dead Reckoning position propagation when GPS drops out
        # -------------------------------------------------------------
        if self._latest_gps and self._latest_gps.fix_valid and (now - self._latest_gps.timestamp) < 2.0:
            lat = self._latest_gps.lat
            lon = self._latest_gps.lon
            self._est_lat = lat
            self._est_lon = lon
            self._est_heading_deg = self._latest_gps.heading_deg
        else:
            # Dead reckoning: propagate coordinates based on heading and forward displacement
            heading_rad = math.radians(self._est_heading_deg)
            displacement_m = (speed / 3.6) * dt
            d_lat = (displacement_m * math.cos(heading_rad)) / 111000.0
            d_lon = (displacement_m * math.sin(heading_rad)) / 83000.0
            self._est_lat += d_lat
            self._est_lon += d_lon
            lat = self._est_lat
            lon = self._est_lon

        # -------------------------------------------------------------
        # 3. Pitch and Slope Rollback detection
        # -------------------------------------------------------------
        pitch = self._latest_imu.pitch_deg if self._latest_imu else 0.0

        if self._latest_imu and self._latest_imu.pitch_deg > 5.0 and self._latest_imu.accel_y < -0.15:
            # Vehicle rolling back on slope
            est_reverse_speed_mps = abs(self._latest_imu.accel_y) * dt
            self._accumulated_rollback_m += est_reverse_speed_mps * dt

        # -------------------------------------------------------------
        # 4. Seatbelt, Handbrake, and Turn Signals
        # -------------------------------------------------------------
        seatbelt = self._latest_obd.seatbelt_fastened if self._latest_obd else True
        handbrake = self._latest_obd.handbrake_active if self._latest_obd else False
        turn_sig = (
            (self._latest_obd.turn_signal_left or self._latest_obd.turn_signal_right)
            if self._latest_obd
            else False
        )

        return FusedVehicleState(
            timestamp=now,
            speed_kmh=round(speed, 1),
            is_stopped=is_stopped,
            pitch_deg=round(pitch, 1),
            seatbelt_fastened=seatbelt,
            handbrake_active=handbrake,
            turn_signal_active=turn_sig,
            lat=lat,
            lon=lon,
            rollback_distance_meters=round(self._accumulated_rollback_m, 2),
            source_quality=quality,
            standstill_confidence=1.0 if is_stopped else 0.0,
        )
