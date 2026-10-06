"""Rule Engine orchestrating plugin execution, exercise filtering, and event manager integration."""

import logging
from pathlib import Path

from driving_eval.core.config_schema import RulesManifest
from driving_eval.rules.base_rule import BaseRulePlugin, EvaluationContext
from driving_eval.rules.event_manager import EventManager, ProcessedViolationEvent
from driving_eval.rules.plugins.cone_touch import ConeTouchRulePlugin
from driving_eval.rules.plugins.seatbelt import SeatbeltRulePlugin
from driving_eval.rules.plugins.standard_rules import (
    CriticalCollisionRulePlugin,
    HillRollbackRulePlugin,
    IndicatorMissedRulePlugin,
    SpeedExceededRulePlugin,
    StopLineRulePlugin,
)

logger = logging.getLogger("driving_eval.rules.engine")


class RuleEngine:
    """Central engine coordinating rule evaluation, filtering, and event emission."""

    def __init__(self, rules_manifest_path: str | Path = "config/rules.yaml"):
        self.manifest = RulesManifest.load_from_yaml(rules_manifest_path)
        self.event_manager = EventManager()
        self._plugins: dict[str, BaseRulePlugin] = {}

        # Register standard built-in plugins
        self.register_plugin(ConeTouchRulePlugin())
        self.register_plugin(SeatbeltRulePlugin())
        self.register_plugin(StopLineRulePlugin())
        self.register_plugin(HillRollbackRulePlugin())
        self.register_plugin(SpeedExceededRulePlugin())
        self.register_plugin(IndicatorMissedRulePlugin())
        self.register_plugin(CriticalCollisionRulePlugin())

    def register_plugin(self, plugin: BaseRulePlugin) -> None:
        """Registers a rule plugin."""
        self._plugins[plugin.rule_code] = plugin
        logger.debug("Plugin ro'yxatdan o'tkazildi: %s", plugin.rule_code)

    def evaluate(self, ctx: EvaluationContext) -> list[ProcessedViolationEvent]:
        """Runs all applicable rule plugins for current exercise and returns new events."""
        emitted_events: list[ProcessedViolationEvent] = []

        for rule in self.manifest.rules:
            # 1. Check exercise binding filter
            if rule.exercise_binding and ctx.current_exercise not in rule.exercise_binding:
                # Rule is not active in this exercise
                continue

            plugin = self._plugins.get(rule.code)
            if not plugin:
                # No evaluator registered for this rule yet
                continue

            # 2. Evaluate plugin
            result = plugin.evaluate(ctx)

            # 3. Process through EventManager (dedup, debounce, cooldown, suspect check)
            event = self.event_manager.process_evaluation(
                rule=rule,
                result=result,
                exercise=ctx.current_exercise,
                timestamp=ctx.timestamp,
            )

            if event:
                emitted_events.append(event)

        return emitted_events
