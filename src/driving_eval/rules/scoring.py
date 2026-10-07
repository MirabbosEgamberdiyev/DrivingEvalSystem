"""Scoring engine and exam evaluation logic.

Calculates real-time candidate scores, tracks critical violations,
and isolates SUSPECT events for inspector review without penalizing the candidate.
"""

import logging
from dataclasses import dataclass

from driving_eval.core.config_schema import ScoringConfig
from driving_eval.rules.event_manager import ProcessedViolationEvent

logger = logging.getLogger("driving_eval.rules.scoring")


@dataclass
class ScoreSnapshot:
    current_score: int
    total_penalty: int
    confirmed_violations_count: int
    critical_violations_count: int
    suspect_events_count: int
    is_passing: bool
    is_terminated: bool


class ScoringEngine:
    """Maintains active session score, penalty ledger, and PASS/FAIL determination."""

    def __init__(self, config: ScoringConfig):
        self.config = config
        self.start_score = config.start_score
        self.pass_score = config.pass_score

        self._confirmed_violations: list[ProcessedViolationEvent] = []
        self._suspect_events: list[ProcessedViolationEvent] = []
        self._total_penalty: int = 0
        self._critical_count: int = 0

    @property
    def current_score(self) -> int:
        return max(0, self.start_score - self._total_penalty)

    @property
    def total_penalty(self) -> int:
        return self._total_penalty

    @property
    def confirmed_violations(self) -> list[ProcessedViolationEvent]:
        return list(self._confirmed_violations)

    @property
    def suspect_events(self) -> list[ProcessedViolationEvent]:
        return list(self._suspect_events)

    @property
    def is_passing(self) -> bool:
        """Candidate PASSES only if final score >= pass_score AND 0 critical violations."""
        return (self.current_score >= self.pass_score) and (self._critical_count == 0)






    @property
    def is_terminated(self) -> bool:
        """True if any critical violation has occurred."""
        return self._critical_count > 0

    def apply_event(self, event: ProcessedViolationEvent) -> ScoreSnapshot:
        """Applies a processed event to the scoring ledger."""
        if event.status == "CONFIRMED":
            self._confirmed_violations.append(event)
            self._total_penalty += event.penalty
            if event.critical:
                self._critical_count += 1
                logger.warning("KRITIK QOIDABUZARLIK! Kod: %s. Test to'xtatiladi.", event.rule_code)
        elif event.status == "SUSPECT":
            # SUSPECT: NO penalty deducted! Recorded for inspector review.
            self._suspect_events.append(event)
            logger.info("SUSPECT hodisa qayd etildi (Jarima yozilmadi): %s", event.rule_code)

        return self.get_snapshot()

    def get_snapshot(self) -> ScoreSnapshot:
        return ScoreSnapshot(
            current_score=self.current_score,
            total_penalty=self._total_penalty,
            confirmed_violations_count=len(self._confirmed_violations),
            critical_violations_count=self._critical_count,
            suspect_events_count=len(self._suspect_events),
            is_passing=self.is_passing,
            is_terminated=self.is_terminated,
        )
