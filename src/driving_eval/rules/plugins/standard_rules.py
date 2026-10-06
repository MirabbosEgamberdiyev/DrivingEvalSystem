"""Rule plugins: STOP_LINE_VIOLATION, HILL_ROLLBACK, SPEED_EXCEEDED, INDICATOR_MISSED, CRITICAL_COLLISION."""

from driving_eval.rules.base_rule import BaseRulePlugin, EvaluationContext, RuleEvaluationResult


class StopLineRulePlugin(BaseRulePlugin):
    @property
    def rule_code(self) -> str:
        return "STOP_LINE_VIOLATION"

    def evaluate(self, ctx: EvaluationContext) -> RuleEvaluationResult:
        stop_line_dets = [d for d in ctx.detections if d.label.lower() in ("stop_line", "solid_line")]
        for det in stop_line_dets:
            # Check if line intersects vehicle front bumper (y > 670 px in 720p front camera)
            if det.bbox.y2 >= 670 and ctx.vehicle_state.speed_kmh > 0.5:
                is_suspect = det.confidence < 0.82
                return RuleEvaluationResult(
                    violated=True,
                    is_suspect=is_suspect,
                    confidence=det.confidence,
                    camera=det.camera,
                    track_id=det.track_id,
                    details=f"Stop chizig'i bosildi (y: {det.bbox.y2:.0f}px, tezlik: {ctx.vehicle_state.speed_kmh:.1f} km/h)",
                    evidence_metadata={"line_y": det.bbox.y2, "speed": ctx.vehicle_state.speed_kmh},
                )
        return RuleEvaluationResult(violated=False)


class HillRollbackRulePlugin(BaseRulePlugin):
    @property
    def rule_code(self) -> str:
        return "HILL_ROLLBACK"

    def evaluate(self, ctx: EvaluationContext) -> RuleEvaluationResult:
        if ctx.current_exercise == "ESTAKADA" and ctx.vehicle_state.rollback_distance_meters > 0.20:
            return RuleEvaluationResult(
                violated=True,
                is_suspect=False,
                confidence=0.95,
                camera="REAR",
                details=f"Estakadada orqaga sirg'alish masofasi: {ctx.vehicle_state.rollback_distance_meters:.2f} metr (chegara: 0.20m)",
                evidence_metadata={"rollback_m": ctx.vehicle_state.rollback_distance_meters},
            )
        return RuleEvaluationResult(violated=False)


class SpeedExceededRulePlugin(BaseRulePlugin):
    @property
    def rule_code(self) -> str:
        return "SPEED_EXCEEDED"

    def evaluate(self, ctx: EvaluationContext) -> RuleEvaluationResult:
        max_speed_kmh = 20.0  # Autodrome speed limit
        if ctx.vehicle_state.speed_kmh > max_speed_kmh:
            return RuleEvaluationResult(
                violated=True,
                is_suspect=False,
                confidence=1.0,
                camera="FRONT",
                details=f"Tezlik oshirildi: {ctx.vehicle_state.speed_kmh:.1f} km/h (maksimal: {max_speed_kmh:.0f} km/h)",
                evidence_metadata={"speed_kmh": ctx.vehicle_state.speed_kmh},
            )
        return RuleEvaluationResult(violated=False)


class IndicatorMissedRulePlugin(BaseRulePlugin):
    @property
    def rule_code(self) -> str:
        return "INDICATOR_MISSED"

    def evaluate(self, ctx: EvaluationContext) -> RuleEvaluationResult:
        # If turning in TURN_90 or starting and turn signal not active
        if ctx.current_exercise in ("TURN_90", "START") and ctx.vehicle_state.speed_kmh > 2.0:
            if not ctx.vehicle_state.turn_signal_active:
                return RuleEvaluationResult(
                    violated=True,
                    is_suspect=False,
                    confidence=0.90,
                    camera="FRONT",
                    details=f"{ctx.current_exercise} mashqida burilish chirog'i yoqilmadi",
                    evidence_metadata={"exercise": ctx.current_exercise},
                )
        return RuleEvaluationResult(violated=False)


class CriticalCollisionRulePlugin(BaseRulePlugin):
    @property
    def rule_code(self) -> str:
        return "CRITICAL_COLLISION"

    def evaluate(self, ctx: EvaluationContext) -> RuleEvaluationResult:
        obstacle_dets = [d for d in ctx.detections if d.label.lower() in ("barrier", "wall", "curb_hard")]
        for det in obstacle_dets:
            if det.bbox.y2 > 680 and det.confidence >= 0.85:
                return RuleEvaluationResult(
                    violated=True,
                    is_suspect=False,
                    confidence=det.confidence,
                    camera=det.camera,
                    track_id=det.track_id,
                    details=f"To'siqqa to'qnashuv aniqlandi! ({det.label})",
                    evidence_metadata={"obstacle": det.label, "confidence": det.confidence},
                )
        return RuleEvaluationResult(violated=False)
