"""Exercise zone tracking and sequence validator.

Tracks exercises (START, ESTAKADA, ZMEIKA, TURN_90, PARALLEL_PARKING, GARAGE_REVERSE, STOP, FINISH),
detects sequence breaking, and signals finish line arrival.
"""

import math
from dataclasses import dataclass

from driving_eval.core.config_schema import ExercisesConfig
from driving_eval.hardware.sensor_fusion import FusedVehicleState


@dataclass
class GeofenceZone:
    code: str
    lat: float
    lon: float
    radius_meters: float


class ExerciseDetector:
    """Monitors vehicle location against autodrome exercise zones."""

    def __init__(self, config: ExercisesConfig):
        self.config = config
        self.sequence = config.sequence
        self._current_index: int = 0
        self._current_exercise: str = self.sequence[0]
        self._visited_exercises: list[str] = [self.sequence[0]]

        # Autodrome default zones (Tashkent reference coordinates with relative offsets)
        # 1 deg lat ~ 111,000 m, 1 deg lon ~ 83,000 m
        base_lat = 41.311081
        base_lon = 69.240562

        self._zones: dict[str, GeofenceZone] = {}
        for idx, code in enumerate(self.sequence):
            # Each exercise staggered by ~30 meters along autodrome track
            offset_m = idx * 35.0
            lat_offset = offset_m / 111000.0
            self._zones[code] = GeofenceZone(
                code=code,
                lat=base_lat + lat_offset,
                lon=base_lon,
                radius_meters=self.config.geofence_tolerance_meters + 15.0,
            )

    @property
    def current_exercise(self) -> str:
        return self._current_exercise

    @property
    def visited_exercises(self) -> list[str]:
        return list(self._visited_exercises)

    def is_in_finish_zone(self, lat: float, lon: float) -> bool:
        """Returns True if the vehicle is within the geofence of the FINISH exercise."""
        finish_zone = self._zones.get("FINISH")
        if not finish_zone:
            return False
        dist = self._distance_meters(lat, lon, finish_zone.lat, finish_zone.lon)
        return dist <= finish_zone.radius_meters

    def can_finalize_test(self, state: FusedVehicleState) -> bool:
        """Test can ONLY be finalized when in finish zone AND vehicle has stopped."""
        in_finish = self.is_in_finish_zone(state.lat, state.lon) or (self._current_exercise == "FINISH")
        return in_finish and state.is_stopped

    def update_location(
        self, state: FusedVehicleState
    ) -> tuple[str, bool, str]:
        """Updates location and returns (current_exercise, sequence_violation_occurred, message)."""
        nearest_exercise = self._find_nearest_zone(state.lat, state.lon)
        if not nearest_exercise or nearest_exercise == self._current_exercise:
            return self._current_exercise, False, ""

        # Check sequence
        try:
            target_idx = self.sequence.index(nearest_exercise)
        except ValueError:
            return self._current_exercise, False, ""

        expected_idx = self._current_index + 1
        if target_idx == expected_idx:
            # Proper sequence progression
            self._current_index = target_idx
            self._current_exercise = nearest_exercise
            self._visited_exercises.append(nearest_exercise)
            return self._current_exercise, False, f"Mashq boshlandi: {nearest_exercise}"
        elif target_idx > expected_idx:
            # Exercise skipped! Critical sequence breach
            skipped = self.sequence[self._current_index + 1 : target_idx]
            msg = f"Mashqlar ketma-ketligi buzildi! {', '.join(skipped)} o'tkazib yuborildi."
            self._current_index = target_idx
            self._current_exercise = nearest_exercise
            self._visited_exercises.append(nearest_exercise)
            return self._current_exercise, True, msg
        else:
            # Re-entering previously visited zone (e.g. driving backwards)
            return self._current_exercise, False, ""

    def force_set_exercise(self, exercise_code: str) -> None:
        """Manual / simulated override of active exercise."""
        if exercise_code in self.sequence:
            self._current_exercise = exercise_code
            self._current_index = self.sequence.index(exercise_code)
            if exercise_code not in self._visited_exercises:
                self._visited_exercises.append(exercise_code)

    def _find_nearest_zone(self, lat: float, lon: float) -> str | None:
        for code, zone in self._zones.items():
            dist = self._distance_meters(lat, lon, zone.lat, zone.lon)
            if dist <= zone.radius_meters:
                return code
        return None

    @staticmethod
    def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine formula approximation for autodrome distance in meters."""
        dy = (lat2 - lat1) * 111000.0
        dx = (lon2 - lon1) * 83000.0
        return math.hypot(dx, dy)
