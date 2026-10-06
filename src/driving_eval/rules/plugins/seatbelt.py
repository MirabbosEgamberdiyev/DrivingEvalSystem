"""Rule plugin: SEATBELT_UNFASTENED."""

from driving_eval.rules.base_rule import BaseRulePlugin, EvaluationContext, RuleEvaluationResult


class SeatbeltRulePlugin(BaseRulePlugin):
    @property
    def rule_code(self) -> str:
        return "SEATBELT_UNFASTENED"

    def evaluate(self, ctx: EvaluationContext) -> RuleEvaluationResult:
        # If seatbelt is not fastened while car is moving or starting
        if not ctx.vehicle_state.seatbelt_fastened:
            return RuleEvaluationResult(
                violated=True,
                is_suspect=False,
                confidence=1.0,
                camera="FRONT",
                details="Xavfsizlik kamari ulanmagan holatda harakatlanish",
                evidence_metadata={"seatbelt_fastened": False, "speed_kmh": ctx.vehicle_state.speed_kmh},
            )
        return RuleEvaluationResult(violated=False)
