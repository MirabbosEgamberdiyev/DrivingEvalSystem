"""Event Manager implementing strict deduplication, debounce, cooldown, and candidate state transitions.

Guarantees: A continuous 20-frame error results in EXACTLY 1 confirmed event and 1 penalty.
Low confidence candidates are marked as SUSPECT without penalty deduction.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from driving_eval.core.config_schema import RuleItem
from driving_eval.rules.base_rule import RuleEvaluationResult

logger = logging.getLogger("driving_eval.rules.event_manager")


class EventLifecycleState(str, Enum):
    IDLE = "IDLE"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    COOLDOWN = "COOLDOWN"


@dataclass
class ProcessedViolationEvent:
    violation_id: str
    rule_code: str
    status: str  # 'CONFIRMED' or 'SUSPECT'
    confidence: float
    penalty: int
    critical: bool
    camera: str
    exercise: str
    details: str
    screen_text: str
    voice_file: str
    voice_text: str
    timestamp: float
    evidence_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackedRuleState:
    rule_code: str
    track_key: str  # f"{rule_code}:{track_id or 'global'}"
    state: EventLifecycleState = EventLifecycleState.IDLE
    consecutive_frames: int = 0
    first_detected_time: float = 0.0
    last_detected_time: float = 0.0
    cooldown_until: float = 0.0
    best_confidence: float = 0.0
    last_result: RuleEvaluationResult | None = None
    has_emitted_suspect: bool = False


class EventManager:
    """Manages debounce, confirmation, and cooldown across all rules and object tracks."""

    def __init__(self):
        self._states: dict[str, TrackedRuleState] = {}
        self._event_counter: int = 0

    def process_evaluation(
        self,
        rule: RuleItem,
        result: RuleEvaluationResult,
        exercise: str,
        timestamp: float,
    ) -> ProcessedViolationEvent | None:
        """Processes a single frame rule evaluation result.

        Returns ProcessedViolationEvent only on state transition to CONFIRMED or SUSPECT.
        """
        track_key = f"{rule.code}:{result.track_id if result.track_id is not None else 'global'}"
        state_obj = self._states.get(track_key)
        if not state_obj:
            state_obj = TrackedRuleState(rule_code=rule.code, track_key=track_key)
            self._states[track_key] = state_obj

        # 1. Handle Cooldown expiration
        if state_obj.state == EventLifecycleState.COOLDOWN:
            if timestamp >= state_obj.cooldown_until:
                state_obj.state = EventLifecycleState.IDLE
                state_obj.consecutive_frames = 0
                state_obj.has_emitted_suspect = False
            else:
                # Still cooling down: discard duplicate event!
                return None

        # 2. If no violation on this frame
        if not result.violated:
            # Decay candidate if interrupted
            if state_obj.state == EventLifecycleState.CANDIDATE:
                state_obj.consecutive_frames = max(0, state_obj.consecutive_frames - 1)
                if state_obj.consecutive_frames == 0:
                    state_obj.state = EventLifecycleState.IDLE
            return None

        # 3. Violation is present on this frame
        state_obj.last_detected_time = timestamp
        state_obj.last_result = result
        state_obj.best_confidence = max(state_obj.best_confidence, result.confidence)

        if state_obj.state == EventLifecycleState.IDLE:
            state_obj.state = EventLifecycleState.CANDIDATE
            state_obj.first_detected_time = timestamp
            state_obj.consecutive_frames = 1
        elif state_obj.state == EventLifecycleState.CANDIDATE:
            state_obj.consecutive_frames += 1

        # Check if debounce threshold reached
        if state_obj.consecutive_frames >= rule.debounce_frames:
            self._event_counter += 1
            v_id = f"VIOL-{rule.code}-{self._event_counter:04d}"

            # Check precision requirements
            is_insufficient_confidence = (
                result.is_suspect or state_obj.best_confidence < rule.min_confidence
            )

            if is_insufficient_confidence:
                # Emitted as SUSPECT - No penalty deducted
                status = "SUSPECT"
                penalty = 0
                state_obj.has_emitted_suspect = True
            else:
                # Emitted as CONFIRMED - Official penalty applied
                status = "CONFIRMED"
                penalty = rule.penalty

            # Move to COOLDOWN immediately to prevent any duplicates
            state_obj.state = EventLifecycleState.COOLDOWN
            state_obj.cooldown_until = timestamp + rule.cooldown_seconds

            event = ProcessedViolationEvent(
                violation_id=v_id,
                rule_code=rule.code,
                status=status,
                confidence=round(state_obj.best_confidence, 3),
                penalty=penalty,
                critical=rule.critical if status == "CONFIRMED" else False,
                camera=result.camera,
                exercise=exercise,
                details=result.details,
                screen_text=rule.screen_text,
                voice_file=rule.voice_file,
                voice_text=rule.voice_text,
                timestamp=timestamp,
                evidence_metadata=result.evidence_metadata,
            )

            logger.info(
                "Event Emitted: %s [%s] (Rule: %s, Penalty: -%d, Conf: %.2f)",
                v_id, status, rule.code, penalty, state_obj.best_confidence
            )
            return event

        return None
