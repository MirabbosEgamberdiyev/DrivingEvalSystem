"""Exercise zone tracking, sequence validation, and active rules binding.

Tracks the 8 official autodrome exercises:
1. START: Start position, seatbelt, handbrake release, left turn signal
2. ESTAKADA: Hill stop and restart without >20cm rollback
3. ZMEIKA: Slalom course between cones
4. TURN_90: 90-degree left and right turns
5. PARALLEL_PARKING: Parallel parking bay
6. GARAGE_REVERSE: Reverse bay parking into 90-degree garage
7. STOP: Stop line before intersection / traffic light
8. FINISH: Finish line and final stop

Monitors geofences, heading alignment, sequence progression, and binds active rules.
"""

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from driving_eval.core.config_schema import ExercisesConfig
from driving_eval.hardware.sensor_fusion import FusedVehicleState


class ExerciseStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass
class GeofenceZone:
    code: str
    lat: float
    lon: float
    radius_meters: float
    expected_heading_deg: float = 0.0
    heading_tolerance_deg: float = 60.0


# Official exercise rule passport mappings
EXERCISE_RULES_MAP: dict[str, list[str]] = {
    "START": ["SEATBELT_UNFASTENED", "START_SIGNAL_OMITTED", "HANDBRAKE_NOT_RELEASED"],
    "ESTAKADA": ["ESTAKADA_ROLLBACK", "ESTAKADA_STALL", "SEATBELT_UNFASTENED"],
    "ZMEIKA": ["CONE_TOUCH", "LINE_TOUCH", "SEATBELT_UNFASTENED"],
    "TURN_90": ["LINE_TOUCH", "CONE_TOUCH", "SEATBELT_UNFASTENED"],
    "PARALLEL_PARKING": ["PARKING_LINE_TOUCH", "CONE_TOUCH", "SEATBELT_UNFASTENED"],
    "GARAGE_REVERSE": ["PARKING_LINE_TOUCH", "CONE_TOUCH", "SEATBELT_UNFASTENED"],
    "STOP": ["STOP_LINE_VIOLATION", "RED_LIGHT_VIOLATION", "SEATBELT_UNFASTENED"],
    "FINISH": ["FINISH_PARKING_INCORRECT", "SEATBELT_UNFASTENED"],
}

GLOBAL_ACTIVE_RULES: set[str] = {
    "SEATBELT_UNFASTENED",
    "SPEED_LIMIT_EXCEEDED",
    "UNAUTHORIZED_STOP",
}


class ExerciseDetector:
    """Monitors vehicle location, sequence, and active rules against autodrome exercises."""

    def __init__(self, config: ExercisesConfig):
        self.config = config
        self.sequence = list(config.sequence)
        self._current_index: int = 0
        self._current_exercise: str = self.sequence[0]
        self._visited_exercises: list[str] = [self.sequence[0]]
        self._exercise_statuses: dict[str, ExerciseStatus] = {
            code: (ExerciseStatus.IN_PROGRESS if code == self.sequence[0] else ExerciseStatus.PENDING)
            for code in self.sequence
        }

        self._zones: dict[str, GeofenceZone] = {}
        loaded_from_file = False
        map_file = getattr(self.config, "autodrome_map_file", None)
        if map_file:
            map_path = Path(map_file)
            if map_path.exists():
                try:
                    with open(map_path, encoding="utf-8") as f:
                        map_data = json.load(f)
                    zones_data = map_data.get("zones", {})
                    for code in self.sequence:
                        if code in zones_data:
                            zd = zones_data[code]
                            self._zones[code] = GeofenceZone(
                                code=code,
                                lat=float(zd["lat"]),
                                lon=float(zd["lon"]),
                                radius_meters=float(zd.get("radius_meters", self.config.geofence_tolerance_meters + 15.0)),
                                expected_heading_deg=float(zd.get("expected_heading_deg", 0.0)),
                                heading_tolerance_deg=float(zd.get("heading_tolerance_deg", 75.0)),
                            )
                    if len(self._zones) == len(self.sequence):
                        loaded_from_file = True
                except Exception:
                    loaded_from_file = False

        if not loaded_from_file:
            # Reference autodrome coordinates (Tashkent Autodrome baseline fallback)
            base_lat = 41.311081
            base_lon = 69.240562
            self._zones = {}
            for idx, code in enumerate(self.sequence):
                # Staggered by ~35 meters along course
                offset_m = idx * 35.0
                lat_offset = offset_m / 111000.0
                self._zones[code] = GeofenceZone(
                    code=code,
                    lat=base_lat + lat_offset,
                    lon=base_lon,
                    radius_meters=self.config.geofence_tolerance_meters + 15.0,
                    expected_heading_deg=0.0,
                    heading_tolerance_deg=75.0,
                )

    @property
    def current_exercise(self) -> str:
        return self._current_exercise

    @property
    def visited_exercises(self) -> list[str]:
        return list(self._visited_exercises)

    @property
    def exercise_statuses(self) -> dict[str, ExerciseStatus]:
        return dict(self._exercise_statuses)

    def is_rule_active_for_current_exercise(self, rule_code: str, rule_bound_exercise: str | None = None) -> bool:
        """Determines if a rule should be evaluated during the current exercise.

        If a rule has a specific exercise bound (e.g. 'ESTAKADA'), it is ONLY active
        when the vehicle is currently executing that exercise.
        """
        # If rule explicitly targets an exercise, enforce matching
        if rule_bound_exercise and rule_bound_exercise != "ALL":
            return self._current_exercise == rule_bound_exercise

        # Global rules always active
        if rule_code in GLOBAL_ACTIVE_RULES:
            return True

        # Check mapped rules for current exercise
        mapped_rules = EXERCISE_RULES_MAP.get(self._current_exercise, [])
        return rule_code in mapped_rules

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

    def check_heading(self, exercise_code: str, current_heading_deg: float) -> bool:
        """Verifies vehicle enters the exercise zone in the correct travel direction."""
        zone = self._zones.get(exercise_code)
        if not zone:
            return True
        diff = abs((current_heading_deg - zone.expected_heading_deg + 180.0) % 360.0 - 180.0)
        return diff <= zone.heading_tolerance_deg

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
            self._exercise_statuses[self._current_exercise] = ExerciseStatus.COMPLETED
            self._current_index = target_idx
            self._current_exercise = nearest_exercise
            self._exercise_statuses[nearest_exercise] = ExerciseStatus.IN_PROGRESS
            self._visited_exercises.append(nearest_exercise)
            return self._current_exercise, False, f"Mashq boshlandi: {nearest_exercise}"
        elif target_idx > expected_idx:
            # Exercise skipped! Critical sequence breach
            skipped = self.sequence[self._current_index + 1 : target_idx]
            for sk in skipped:
                self._exercise_statuses[sk] = ExerciseStatus.SKIPPED
            self._exercise_statuses[self._current_exercise] = ExerciseStatus.COMPLETED

            msg = f"Mashqlar ketma-ketligi buzildi! {', '.join(skipped)} o'tkazib yuborildi."
            self._current_index = target_idx
            self._current_exercise = nearest_exercise
            self._exercise_statuses[nearest_exercise] = ExerciseStatus.IN_PROGRESS
            self._visited_exercises.append(nearest_exercise)
            return self._current_exercise, True, msg
        else:
            # Re-entering previously visited zone (e.g. driving backwards)
            return self._current_exercise, False, ""

    def force_set_exercise(self, exercise_code: str) -> None:
        """Manual / simulated override of active exercise."""
        if exercise_code in self.sequence:
            self._exercise_statuses[self._current_exercise] = ExerciseStatus.COMPLETED
            self._current_exercise = exercise_code
            self._current_index = self.sequence.index(exercise_code)
            self._exercise_statuses[exercise_code] = ExerciseStatus.IN_PROGRESS
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
        """Haversine distance approximation for autodrome in meters."""
        dy = (lat2 - lat1) * 111000.0
        dx = (lon2 - lon1) * 83000.0
        return math.hypot(dx, dy)
