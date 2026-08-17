"""Decision router for evaluation results.

Applies confidence thresholds to route questions to
PASS, REVIEW, or REJECT based on scores and confidence.
"""

from __future__ import annotations

from src.utils.config import ThresholdConfig
from src.utils.models import Decision


class DecisionRouter:
    """
    Routes evaluation results to decisions based on configurable thresholds.

    Decision Matrix:
    - PASS: High confidence + high score
    - REJECT: High confidence + low score
    - REVIEW: Low confidence OR borderline score

    Thresholds are configurable and can be tuned based on
    business requirements (precision vs. reviewer workload).
    """

    def __init__(self, config: ThresholdConfig):
        self.config = config

    def decide(self, score: float, confidence: float) -> Decision:
        """
        Make a routing decision based on score and confidence.

        Args:
            score: Quality score (0-100)
            confidence: Model confidence (0-1)

        Returns:
            Decision: PASS, REVIEW, or REJECT
        """
        # High confidence + high score → PASS
        if (
            confidence >= self.config.pass_confidence_min
            and score >= self.config.pass_score_min
        ):
            return Decision.PASS

        # High confidence + low score → REJECT
        if (
            confidence >= self.config.reject_confidence_min
            and score <= self.config.reject_score_max
        ):
            return Decision.REJECT

        # Low confidence → always REVIEW
        if confidence < self.config.review_confidence_max:
            return Decision.REVIEW

        # Borderline cases → REVIEW
        return Decision.REVIEW

    def needs_escalation(self, score: float, confidence: float) -> bool:
        """
   
        Determine if a Tier 2 result needs Tier 3 (LLM) escalation.

        Escalation happens when confidence is in the "uncertain" range,
        meaning Tier 2 isn't confident enough to make a decision alone.
        """
        return (
            self.config.tier3_confidence_min
            <= confidence
            < self.config.tier3_confidence_max
        )
