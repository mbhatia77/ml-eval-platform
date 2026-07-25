"""Main evaluation engine orchestrating the tiered evaluation pipeline."""

from __future__ import annotations

import time
import logging
from typing import Optional

from src.utils.models import (
    Decision,
    DimensionScore,
    EvaluationInput,
    EvaluationResult,
    FeatureVector,
)
from src.utils.config import AppConfig
from src.evaluation.tier1_rules import Tier1RuleEngine
from src.evaluation.tier2_ml import Tier2MLModel
from src.evaluation.tier3_llm import Tier3LLMJudge
from src.evaluation.decision_router import DecisionRouter

logger = logging.getLogger(__name__)


class EvaluationEngine:
    """
    Orchestrates the tiered evaluation pipeline.

    Tier 1: Rule-based checks (grammar, format, length) — fast, cheap
    Tier 2: ML model scoring (DeBERTa + XGBoost) — medium cost
    Tier 3: LLM-as-judge (GPT-4/Claude) — expensive, only for uncertain cases
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.tier1 = Tier1RuleEngine()
        self.tier2 = Tier2MLModel(config.model)
        self.tier3 = Tier3LLMJudge(config.model)
        self.router = DecisionRouter(config.thresholds)

    async def evaluate(
        self,
        input: EvaluationInput,
        features: FeatureVector,
    ) -> EvaluationResult:
        """
        Run the full evaluation pipeline on a single question.

        Flow:
        1. Tier 1 rule checks — reject obvious failures immediately
        2. Tier 2 ML scoring — get scores + confidence
        3. If confidence is in uncertain range, escalate to Tier 3
        4. Route to decision (pass/review/reject)
        """
        start_time = time.perf_counter()
        tier_used = 1

        # --- Tier 1: Rule-based checks ---
        tier1_result = self.tier1.evaluate(input, features)
        if tier1_result.is_rejected:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return self._build_result(
                evaluation_id=input.evaluation_id,
                scores=tier1_result.dimension_scores,
                quality_score=tier1_result.quality_score,
                confidence=0.95,
                decision=Decision.REJECT,
                explanation=tier1_result.explanation,
                tier_used=1,
                latency_ms=latency_ms,
            )

        # --- Tier 2: ML Model scoring ---
        tier_used = 2
        tier2_result = await self.tier2.score(input, features)

        # Check if we need Tier 3
        needs_tier3 = self.router.needs_escalation(
            score=tier2_result.quality_score,
            confidence=tier2_result.confidence,
        )

        tier3_result = None
        if needs_tier3:
            tier_used = 3
            tier3_result = await self.tier3.evaluate(input, tier2_result)
            # Blend Tier 2 and Tier 3 scores
            final_score = self._blend_scores(tier2_result, tier3_result)
            final_confidence = max(tier2_result.confidence, tier3_result.confidence)
            explanation = tier3_result.explanation
            dimension_scores = tier3_result.dimension_scores
        else:
            final_score = tier2_result.quality_score
            final_confidence = tier2_result.confidence
            explanation = tier2_result.explanation
            dimension_scores = tier2_result.dimension_scores

        # --- Decision routing ---
        decision = self.router.decide(final_score, final_confidence)
        human_review = decision == Decision.REVIEW

        latency_ms = (time.perf_counter() - start_time) * 1000

        return self._build_result(
            evaluation_id=input.evaluation_id,
            scores=dimension_scores,
            quality_score=final_score,
            confidence=final_confidence,
            decision=decision,
            explanation=explanation,
            tier_used=tier_used,
            latency_ms=latency_ms,
            human_review=human_review,
        )

    def _blend_scores(self, tier2_result, tier3_result) -> float:
        """Blend Tier 2 and Tier 3 scores with weighted average."""
        # Weight Tier 3 more heavily since it's the escalation path
        tier2_weight = 0.3
        tier3_weight = 0.7
        return (
            tier2_result.quality_score * tier2_weight
            + tier3_result.quality_score * tier3_weight
        )

    def _build_result(
        self,
        evaluation_id: str,
        scores: list[DimensionScore],
        quality_score: float,
        confidence: float,
        decision: Decision,
        explanation: str,
        tier_used: int,
        latency_ms: float,
        human_review: bool = False,
    ) -> EvaluationResult:
        """Construct the final evaluation result."""
        return EvaluationResult(
            evaluation_id=evaluation_id or "unknown",
            quality_score=quality_score,
            confidence=confidence,
            decision=decision,
            dimension_scores=scores,
            explanation=explanation,
            human_review_recommended=human_review,
            tier_used=tier_used,
            latency_ms=latency_ms,
        )
