"""Sensor fusion combining GPS, IMU, OBD-II, and camera telemetry.

Produces robust vehicle state estimation (speed, position, slope, seatbelt, signals, rollback).
"""

import time
from dataclasses import dataclass


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


class SensorFusionService:
    """Fuses multi-modal sensor streams into a reliable ground truth state."""

    def __init__(self, speed_stop_threshold_kmh: float = 1.5):
        self.speed_stop_threshold_kmh = speed_stop_threshold_kmh
        self._latest_gps: GPSData | None = None
        self._latest_imu: IMUData | None = None
        self._latest_obd: OBDData | None = None

        self._accumulated_rollback_m: float = 0.0
        self._last_state_time: float = time.monotonic()

    def update_gps(self, data: GPSData) -> None:
        self._latest_gps = data

    def update_imu(self, data: IMUData) -> None:
        self._latest_imu = data

    def update_obd(self, data: OBDData) -> None:
        self._latest_obd = data

    def reset_rollback(self) -> None:
        self._accumulated_rollback_m = 0.0

    def get_fused_state(self, current_timestamp: float) -> FusedVehicleState:
        now = current_timestamp

        # 1. Speed determination (OBD is primary, GPS is fallback)
        if self._latest_obd and (now - self._latest_obd.timestamp) < 1.0:
            speed = max(0.0, self._latest_obd.speed_kmh)
            quality = "OBD_PRIMARY"
        elif self._latest_gps and self._latest_gps.fix_valid and (now - self._latest_gps.timestamp) < 2.0:
            speed = max(0.0, self._latest_gps.speed_kmh)
            quality = "GPS_FALLBACK"
        else:
            speed = 0.0
            quality = "DEGRADED_ZERO"

        is_stopped = speed < self.speed_stop_threshold_kmh

        # 2. Pitch / Inclination
        pitch = self._latest_imu.pitch_deg if self._latest_imu else 0.0

        # 3. Rollback detection on hill (pitch > 5 deg, negative longitudinal acceleration or reverse motion)
        dt = max(0.001, now - self._last_state_time)
        self._last_state_time = now

        if self._latest_imu and self._latest_imu.pitch_deg > 5.0 and self._latest_imu.accel_y < -0.15:
            # Vehicle rolling back on slope
            est_reverse_speed_mps = abs(self._latest_imu.accel_y) * dt
            self._accumulated_rollback_m += est_reverse_speed_mps * dt

        # 4. Seatbelt and Handbrake
        seatbelt = self._latest_obd.seatbelt_fastened if self._latest_obd else True
        handbrake = self._latest_obd.handbrake_active if self._latest_obd else False
        turn_sig = (
            (self._latest_obd.turn_signal_left or self._latest_obd.turn_signal_right)
            if self._latest_obd
            else False
        )

        lat = self._latest_gps.lat if self._latest_gps else 41.311081  # Default Tashkent Autodrome
        lon = self._latest_gps.lon if self._latest_gps else 69.240562

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
        )
