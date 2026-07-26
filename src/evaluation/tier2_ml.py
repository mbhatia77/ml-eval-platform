"""Tier 2: ML Model evaluation engine.

Fine-tuned DeBERTa + XGBoost ensemble for multi-dimensional scoring.
Runs in < 50ms per question (batched inference on GPU).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.utils.config import ModelConfig
from src.utils.models import (
    DimensionScore,
    EvaluationDimension,
    EvaluationInput,
    FeatureVector,
)

logger = logging.getLogger(__name__)


@dataclass
class Tier2Result:
    """Result from ML model evaluation."""
    quality_score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""
    dimension_scores: list[DimensionScore] = field(default_factory=list)


class Tier2MLModel:
    """
    ML-based evaluator using DeBERTa + XGBoost ensemble.

    Architecture:
    - DeBERTa-v3-base: fine-tuned for quality assessment, outputs per-dimension scores
    - XGBoost: trained on engineered features, provides calibrated probabilities
    - Aggregator: weighted combination with Platt-scaled confidence

    The model is loaded once at startup and serves inference requests.
    Batched inference is supported for throughput optimization.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self.deberta_model = None
        self.xgboost_model = None
        self._load_models()

    def _load_models(self):
        """Load trained models from registry."""
        # In production:
        # self.deberta_model = AutoModelForSequenceClassification.from_pretrained(
        #     self.config.tier2_model_path
        # )
        # self.xgboost_model = xgb.Booster()
        # self.xgboost_model.load_model(self.config.tier2_xgboost_path)
        logger.info("Tier 2 models loaded (placeholder mode)")

    async def score(
        self,
        input: EvaluationInput,
        features: FeatureVector,
    ) -> Tier2Result:
        """
        Score a question using the ML ensemble.

        Steps:
        1. Encode question + source with DeBERTa → per-dimension logits
        2. Run XGBoost on engineered features → calibrated scores
        3. Combine with learned weights
        4. Apply Platt scaling for confidence calibration
        """
        # --- DeBERTa scoring (placeholder) ---
        deberta_scores = self._run_deberta(input)

        # --- XGBoost scoring (placeholder) ---
        xgboost_scores = self._run_xgboost(features)

        # --- Ensemble combination ---
        dimension_scores = self._combine_scores(deberta_scores, xgboost_scores)

        # --- Compute overall score and confidence ---
        quality_score = self._compute_quality_score(dimension_scores)
        confidence = self._compute_confidence(dimension_scores)

        # --- Generate explanation ---
        explanation = self._generate_explanation(dimension_scores)

        return Tier2Result(
            quality_score=quality_score,
            confidence=confidence,
            explanation=explanation,
            dimension_scores=dimension_scores,
        )

    def _run_deberta(self, input: EvaluationInput) -> dict[str, float]:
        """Run DeBERTa inference for semantic quality assessment."""
        # In production: tokenize input, run model forward pass
        # Returns logits for each dimension head
        #
        # text = f"[CLS] {input.generated_question} [SEP] {input.source_document} [SEP]"
        # inputs = tokenizer(text, truncation=True, max_length=512)
        # outputs = model(**inputs)
        # dimension_logits = outputs.logits  # shape: (1, 10)

        # Placeholder scores
        return {dim.value: 75.0 for dim in EvaluationDimension}

    def _run_xgboost(self, features: FeatureVector) -> dict[str, float]:
        """Run XGBoost on engineered features."""
        # In production:
        # feature_array = self._features_to_array(features)
        # dmatrix = xgb.DMatrix(feature_array)
        # predictions = self.xgboost_model.predict(dmatrix)

        # Placeholder scores
        return {dim.value: 70.0 for dim in EvaluationDimension}

    def _combine_scores(
        self,
        deberta_scores: dict[str, float],
        xgboost_scores: dict[str, float],
    ) -> list[DimensionScore]:
        """Combine DeBERTa and XGBoost scores with learned weights."""
        # DeBERTa handles semantic dimensions better
        # XGBoost handles surface-level features better
        semantic_dims = {
            EvaluationDimension.CORRECTNESS,
            EvaluationDimension.GROUNDEDNESS,
            EvaluationDimension.RELEVANCE,
            EvaluationDimension.HALLUCINATION,
            EvaluationDimension.COMPLETENESS,
        }

        dimension_scores = []
        for dim in EvaluationDimension:
            deberta_score = deberta_scores.get(dim.value, 50.0)
            xgboost_score = xgboost_scores.get(dim.value, 50.0)

            if dim in semantic_dims:
                combined = deberta_score * 0.7 + xgboost_score * 0.3
            else:
                combined = deberta_score * 0.4 + xgboost_score * 0.6

            # Confidence based on score agreement
            agreement = 1.0 - abs(deberta_score - xgboost_score) / 100.0
            confidence = min(0.95, agreement * 0.9 + 0.1)

            dimension_scores.append(DimensionScore(
                dimension=dim,
                score=round(combined, 2),
                confidence=round(confidence, 3),
            ))

        return dimension_scores

    def _compute_quality_score(self, scores: list[DimensionScore]) -> float:
        """Compute overall quality score from dimension scores."""
        # Weighted average — some dimensions matter more
        weights = {
            EvaluationDimension.CORRECTNESS: 2.0,
            EvaluationDimension.GROUNDEDNESS: 1.8,
            EvaluationDimension.HALLUCINATION: 1.8,
            EvaluationDimension.RELEVANCE: 1.5,
            EvaluationDimension.CLARITY: 1.2,
            EvaluationDimension.COMPLETENESS: 1.0,
            EvaluationDimension.DIFFICULTY: 0.8,
            EvaluationDimension.NON_DUPLICATION: 1.0,
            EvaluationDimension.BIAS_SAFETY: 2.0,
            EvaluationDimension.GRAMMAR: 0.8,
        }

        weighted_sum = sum(s.score * weights.get(s.dimension, 1.0) for s in scores)
        total_weight = sum(weights.get(s.dimension, 1.0) for s in scores)

        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 50.0

    def _compute_confidence(self, scores: list[DimensionScore]) -> float:
        """Compute overall confidence from dimension confidences."""
        if not scores:
            return 0.5
        # Use minimum confidence (weakest link)
        min_conf = min(s.confidence for s in scores)
        avg_conf = sum(s.confidence for s in scores) / len(scores)
        # Blend min and average
        return round(min_conf * 0.4 + avg_conf * 0.6, 3)

    def _generate_explanation(self, scores: list[DimensionScore]) -> str:
        """Generate human-readable explanation of scores."""
        low_scores = [s for s in scores if s.score < 60]
        high_scores = [s for s in scores if s.score >= 80]

        parts = []
        if high_scores:
            dims = ", ".join(s.dimension.value for s in high_scores[:3])
            parts.append(f"Strong on: {dims}")
        if low_scores:
            dims = ", ".join(s.dimension.value for s in low_scores[:3])
            parts.append(f"Weak on: {dims}")

        return ". ".join(parts) if parts else "All dimensions within acceptable range"
