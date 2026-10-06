"""Session Replay Engine and Ground Truth Benchmark Validator.

Plays back simulated or recorded driving test sessions (sensor telemetry,
detected objects, and multi-camera streams) through the full evaluation pipeline:
Tracker -> ExerciseDetector -> RuleEngine -> EventManager -> ScoringEngine.

Computes precision, recall, and F1 metrics against ground-truth scenario annotations
to guarantee 100% precision (zero false penalties) and 0-regression quality gates.
"""

import csv
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from driving_eval.ai.detector_base import BaseDetector, Detection
from driving_eval.ai.exercise_detector import ExerciseDetector
from driving_eval.ai.tracker import SimpleByteTracker
from driving_eval.core.config_schema import SystemConfig
from driving_eval.hardware.sensor_fusion import FusedVehicleState
from driving_eval.rules.base_rule import EvaluationContext
from driving_eval.rules.engine import RuleEngine
from driving_eval.rules.event_manager import ProcessedViolationEvent
from driving_eval.rules.scoring import ScoringEngine

logger = logging.getLogger("driving_eval.replay")


@dataclass
class ReplayFrame:
    """A single discrete time slice in a driving replay session."""

    timestamp: float
    vehicle_state: FusedVehicleState
    exercise: str | None = None
    detections: list[Detection] = field(default_factory=list)
    camera_frames: dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class GroundTruthViolation:
    """An annotated expected violation in a ground-truth replay scenario."""

    rule_code: str
    timestamp_start: float = 0.0
    timestamp_end: float = 0.0
    exercise: str | None = None
    critical: bool = False
    notes: str = ""


@dataclass
class ReplayScenario:
    """A complete self-contained test scenario for regression and evaluation benchmarking."""

    scenario_id: str
    name: str
    description: str
    frames: list[ReplayFrame]
    expected_violations: list[GroundTruthViolation]
    config_path: str | Path = "config/config.yaml"
    rules_path: str | Path = "config/rules.yaml"


@dataclass
class RuleReplayMetrics:
    """Evaluation metrics for a specific driving rule."""

    rule_code: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    suspect_count: int = 0

    @property
    def precision(self) -> float:
        total_predicted = self.true_positives + self.false_positives
        if total_predicted == 0:
            return 1.0  # Perfect precision when zero false alarms were raised
        return self.true_positives / total_predicted

    @property
    def recall(self) -> float:
        total_actual = self.true_positives + self.false_negatives
        if total_actual == 0:
            return 1.0  # Perfect recall when zero events were missed
        return self.true_positives / total_actual

    @property
    def f1_score(self) -> float:
        p = self.precision
        r = self.recall
        if (p + r) == 0:
            return 0.0
        return 2.0 * p * r / (p + r)


@dataclass
class ReplayReport:
    """Comprehensive outcome report of a session replay."""

    scenario_id: str
    scenario_name: str
    total_frames: int
    duration_seconds: float
    final_score: int
    is_passing: bool
    is_terminated: bool
    rule_metrics: dict[str, RuleReplayMetrics]
    confirmed_events: list[ProcessedViolationEvent]
    suspect_events: list[ProcessedViolationEvent]
    timeline_records: list[dict[str, Any]] = field(default_factory=list)

    def summary_markdown(self) -> str:
        """Generates a GitHub-flavored markdown summary table of replay metrics."""
        lines = [
            f"# Replay Benchmark Natijasi: {self.scenario_name} (`{self.scenario_id}`)",
            f"- **Kadrlar soni**: {self.total_frames} ta | **Davomiyligi**: {self.duration_seconds:.1f} soniya",
            f"- **Yakuniy ball**: {self.final_score} / 100 | **Holat**: {'PASS ✅' if self.is_passing else 'FAIL ❌'}",
            f"- **Kritik to'xtatish**: {'HA ⚠️' if self.is_terminated else 'YOʻQ'}",
            f"- **Tasdiqlangan hodisalar**: {len(self.confirmed_events)} ta | **SUSPECT hodisalar**: {len(self.suspect_events)} ta",
            "",
            "| Qoida Kodi | TP | FP | FN | Suspect | Precision | Recall | F1-Score |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for code, m in sorted(self.rule_metrics.items()):
            lines.append(
                f"| `{code}` | {m.true_positives} | {m.false_positives} | {m.false_negatives} | "
                f"{m.suspect_count} | {m.precision:.2f} | {m.recall:.2f} | {m.f1_score:.2f} |"
            )
        return "\n".join(lines)

    def verify_quality_gates(
        self, min_precision: float = 1.0, min_recall: float = 1.0
    ) -> tuple[bool, list[str]]:
        """Validates that all rules strictly meet or exceed precision and recall thresholds."""
        failures: list[str] = []
        for code, m in self.rule_metrics.items():
            if m.precision < min_precision:
                failures.append(
                    f"Rule {code} precision {m.precision:.2f} below gate {min_precision:.2f} (FP={m.false_positives})"
                )
            if m.recall < min_recall:
                failures.append(
                    f"Rule {code} recall {m.recall:.2f} below gate {min_recall:.2f} (FN={m.false_negatives})"
                )
        return len(failures) == 0, failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "total_frames": self.total_frames,
            "duration_seconds": round(self.duration_seconds, 2),
            "final_score": self.final_score,
            "is_passing": self.is_passing,
            "is_terminated": self.is_terminated,
            "confirmed_violations_count": len(self.confirmed_events),
            "suspect_events_count": len(self.suspect_events),
            "metrics": {
                k: {
                    "tp": v.true_positives,
                    "fp": v.false_positives,
                    "fn": v.false_negatives,
                    "suspect": v.suspect_count,
                    "precision": round(v.precision, 3),
                    "recall": round(v.recall, 3),
                    "f1": round(v.f1_score, 3),
                }
                for k, v in self.rule_metrics.items()
            },
        }

    def export_json(self, target_path: Path | str) -> None:
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def export_csv(self, target_path: Path | str) -> None:
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["rule_code", "true_positives", "false_positives", "false_negatives", "suspect_count", "precision", "recall", "f1_score"])
            for code, m in sorted(self.rule_metrics.items()):
                writer.writerow([code, m.true_positives, m.false_positives, m.false_negatives, m.suspect_count, round(m.precision, 3), round(m.recall, 3), round(m.f1_score, 3)])


class SessionReplayer:
    """Execution engine for replaying recorded scenarios through the driving evaluation pipeline."""

    def __init__(
        self,
        rules_path: str | Path = "config/rules.yaml",
        config_path: str | Path = "config/config.yaml",
        detector: BaseDetector | None = None,
    ):
        self.rules_path = Path(rules_path)
        self.config_path = Path(config_path)
        self.detector = detector

    def replay(
        self,
        scenario: ReplayScenario,
        real_time: bool = False,
        playback_rate: float = 1.0,
        frame_callback: Callable[[ReplayFrame, str, int], None] | None = None,
    ) -> ReplayReport:
        """Executes full pipeline replay of a test scenario and returns metrics report."""
        config = SystemConfig.load_from_yaml(scenario.config_path or self.config_path)
        rule_engine = RuleEngine(scenario.rules_path or self.rules_path)
        scoring_engine = ScoringEngine(config.scoring)
        exercise_detector = ExerciseDetector(config.exercises)
        tracker = SimpleByteTracker()

        confirmed_events: list[ProcessedViolationEvent] = []
        suspect_events: list[ProcessedViolationEvent] = []
        timeline_records: list[dict[str, Any]] = []

        total_frames = len(scenario.frames)
        t_start = scenario.frames[0].timestamp if total_frames > 0 else 0.0
        t_end = scenario.frames[-1].timestamp if total_frames > 0 else 0.0
        duration = max(0.0, t_end - t_start)

        prev_timestamp: float | None = None

        for idx, frame in enumerate(scenario.frames):
            if real_time and prev_timestamp is not None and playback_rate > 0.0:
                dt = (frame.timestamp - prev_timestamp) / playback_rate
                if 0.0 < dt < 1.0:
                    time.sleep(dt)
            prev_timestamp = frame.timestamp

            # 1. Update Exercise detector
            detected_exercise, _, _ = exercise_detector.update_location(frame.vehicle_state)
            current_exercise = frame.exercise if frame.exercise is not None else detected_exercise

            # 2. Extract or use Detections
            raw_dets = list(frame.detections)
            if self.detector and frame.camera_frames:
                for cam_name, cam_img in frame.camera_frames.items():
                    dets = self.detector.detect(cam_img, cam_name, frame.timestamp)
                    raw_dets.extend(dets)

            # 3. Update Tracker
            tracked_dets = tracker.update(raw_dets, frame.timestamp)

            # 4. Assemble EvaluationContext
            ctx = EvaluationContext(
                timestamp=frame.timestamp,
                current_exercise=current_exercise,
                vehicle_state=frame.vehicle_state,
                detections=tracked_dets,
                frame_bundle=None,
                calibrations={},
            )

            # 5. Evaluate Rules via RuleEngine
            emitted = rule_engine.evaluate(ctx)

            # 6. Apply to ScoringEngine
            for ev in emitted:
                scoring_engine.apply_event(ev)
                if ev.status == "CONFIRMED":
                    confirmed_events.append(ev)
                    logger.info("Replay tasdiqlangan qoidabuzarlik [%s]: %s (%d ball)", current_exercise, ev.rule_code, ev.penalty)
                elif ev.status == "SUSPECT":
                    suspect_events.append(ev)
                    logger.info("Replay shubhali hodisa [%s]: %s (0 ball)", current_exercise, ev.rule_code)

            timeline_records.append({
                "frame_index": idx,
                "timestamp": frame.timestamp,
                "exercise": current_exercise,
                "speed_kmh": frame.vehicle_state.speed_kmh,
                "score": scoring_engine.current_score,
                "emitted_count": len(emitted),
            })

            if frame_callback:
                frame_callback(frame, current_exercise, scoring_engine.current_score)

        # 7. Compare with Ground Truth Annotations
        metrics = self._compute_benchmark_metrics(scenario.expected_violations, confirmed_events, suspect_events)

        return ReplayReport(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            total_frames=total_frames,
            duration_seconds=duration,
            final_score=scoring_engine.current_score,
            is_passing=scoring_engine.is_passing,
            is_terminated=scoring_engine.is_terminated,
            rule_metrics=metrics,
            confirmed_events=confirmed_events,
            suspect_events=suspect_events,
            timeline_records=timeline_records,
        )

    def _compute_benchmark_metrics(
        self,
        expected: list[GroundTruthViolation],
        confirmed: list[ProcessedViolationEvent],
        suspects: list[ProcessedViolationEvent],
    ) -> dict[str, RuleReplayMetrics]:
        """Calculates TP, FP, FN, and Suspect counts per rule code."""
        # Collect all unique rules mentioned
        all_rules = {exp.rule_code for exp in expected}
        all_rules.update(ev.rule_code for ev in confirmed)
        all_rules.update(ev.rule_code for ev in suspects)

        metrics: dict[str, RuleReplayMetrics] = {r: RuleReplayMetrics(rule_code=r) for r in all_rules}

        # Count suspects
        for s in suspects:
            if s.rule_code in metrics:
                metrics[s.rule_code].suspect_count += 1

        matched_confirmed_indices: set[int] = set()

        # Match each expected violation against confirmed events
        for exp in expected:
            m_obj = metrics[exp.rule_code]
            match_found = False

            for c_idx, ev in enumerate(confirmed):
                if c_idx in matched_confirmed_indices:
                    continue
                if ev.rule_code != exp.rule_code:
                    continue

                # Check exercise or time range matching
                time_matched = True
                if exp.timestamp_end > exp.timestamp_start:
                    time_matched = (exp.timestamp_start - 2.0) <= ev.timestamp <= (exp.timestamp_end + 2.0)

                exercise_matched = True
                if exp.exercise:
                    exercise_matched = (ev.exercise == exp.exercise)

                if time_matched and exercise_matched:
                    match_found = True
                    matched_confirmed_indices.add(c_idx)
                    m_obj.true_positives += 1
                    break

            if not match_found:
                m_obj.false_negatives += 1

        # Any unmatched confirmed events are false positives!
        for c_idx, ev in enumerate(confirmed):
            if c_idx not in matched_confirmed_indices:
                metrics[ev.rule_code].false_positives += 1

        return metrics
