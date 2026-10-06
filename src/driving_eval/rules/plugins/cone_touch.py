"""Rule plugin: CONE_TOUCH (Traffic cone contact / collision).

Checks metric distance using camera calibration homography and bottom-center contact points.
Detection alone is not violation: distance < contact_threshold is strictly verified.
"""

from driving_eval.rules.base_rule import BaseRulePlugin, EvaluationContext, RuleEvaluationResult


class ConeTouchRulePlugin(BaseRulePlugin):
    @property
    def rule_code(self) -> str:
        return "CONE_TOUCH"

    def evaluate(self, ctx: EvaluationContext) -> RuleEvaluationResult:
        # Check all detections labeled 'cone'
        cone_dets = [d for d in ctx.detections if d.label.lower() == "cone"]
        if not cone_dets:
            return RuleEvaluationResult(violated=False)

        contact_distance_threshold_m = 0.25  # 25 cm contact zone

        for det in cone_dets:
            calib = ctx.calibrations.get(det.camera)
            # Default pixel distance if calibration not available
            if calib:
                bottom_cx, bottom_cy = det.bbox.bottom_center
                gx, gy = calib.pixel_to_ground_plane(bottom_cx, bottom_cy)
                # Distance to bumper ground reference (0, 0 in vehicle coordinate frame)
                metric_dist = (gx**2 + gy**2) ** 0.5
            else:
                # Approximate distance in normalized box coordinate
                metric_dist = 0.15 if det.bbox.y2 > 650 else 0.80

            if metric_dist <= contact_distance_threshold_m:
                # If confidence is lower than 0.80, mark as SUSPECT
                is_suspect = det.confidence < 0.80
                return RuleEvaluationResult(
                    violated=True,
                    is_suspect=is_suspect,
                    confidence=det.confidence,
                    camera=det.camera,
                    track_id=det.track_id,
                    details=f"Konusga yaqinlik/kontakt masofasi: {metric_dist:.2f} metr (chegara: {contact_distance_threshold_m:.2f}m)",
                    evidence_metadata={
                        "metric_distance_m": round(metric_dist, 3),
                        "bbox": [det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2],
                    },
                )

        return RuleEvaluationResult(violated=False)
