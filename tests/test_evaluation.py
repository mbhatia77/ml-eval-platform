"""Tests for the evaluation engine."""

from unittest.mock import AsyncMock, Mock

from src.evaluation.decision_router import DecisionRouter
from src.evaluation.engine import EvaluationEngine
from src.evaluation.tier1_rules import Tier1Result, Tier1RuleEngine
from src.evaluation.tier2_ml import Tier2Result
from src.evaluation.tier3_llm import Tier3Result
from src.utils.config import AppConfig, ThresholdConfig
from src.utils.models import (
    Decision,
    DimensionScore,
    DocumentType,
    EvaluationDimension,
    EvaluationInput,
    FeatureVector,
    QuestionMetadata,
)

# --- Fixtures ---


def make_input(
    question: str = "What is the primary function of the mitochondria?",
    source: str = "The mitochondria is the powerhouse of the cell, responsible for producing ATP.",
    answer: str = "The primary function is to produce ATP through cellular respiration.",
) -> EvaluationInput:
    """Create a test evaluation input."""
    return EvaluationInput(
        evaluation_id="test-123",
        source_document=source,
        generated_question=question,
        expected_answer=answer,
        metadata=QuestionMetadata(
            document_type=DocumentType.GENERAL,
            domain="biology",
            language="en",
            generation_model="gpt-4",
            prompt_version="v1.0",
        ),
    )


def make_features() -> FeatureVector:
    """Create placeholder features."""
    return FeatureVector(
        evaluation_id="test-123",
        text_features={"question_char_length": 52.0},
        semantic_features={"source_similarity": 0.8},
        reference_features={"rouge_1": 0.6},
        safety_features={"toxicity_score": 0.01},
        duplicate_features={"minhash_similarity": 0.0},
    )


def make_dimension(score: float, confidence: float) -> DimensionScore:
    return DimensionScore(
        dimension=EvaluationDimension.CORRECTNESS,
        score=score,
        confidence=confidence,
    )


def make_engine() -> EvaluationEngine:
    """Engine with mocked tiers and the real DecisionRouter."""
    engine = EvaluationEngine(AppConfig())
    engine.tier1 = Mock()
    engine.tier2 = Mock()
    engine.tier2.score = AsyncMock()
    engine.tier3 = Mock()
    engine.tier3.evaluate = AsyncMock()
    return engine


# --- Tier 1 Rule Engine Tests ---


class TestTier1Rules:
    """Test rule-based evaluation."""

    def setup_method(self):
        self.engine = Tier1RuleEngine()

    def test_valid_question_passes(self):
        input = make_input()
        result = self.engine.evaluate(input, make_features())
        assert not result.is_rejected

    def test_missing_question_mark_rejects(self):
        input = make_input(question="What is the function of mitochondria")
        result = self.engine.evaluate(input, make_features())
        assert result.is_rejected
        assert "?" in result.explanation

    def test_too_short_question_rejects(self):
        input = make_input(question="Why?")
        result = self.engine.evaluate(input, make_features())
        assert result.is_rejected
        assert "too short" in result.explanation.lower()

    def test_blocklist_pattern_rejects(self):
        input = make_input(question="This is a TODO placeholder question?")
        result = self.engine.evaluate(input, make_features())
        assert result.is_rejected

    def test_verbatim_copy_rejects(self):
        source = "The mitochondria is the powerhouse of the cell."
        question = "The mitochondria is the powerhouse of the cell?"
        input = make_input(question=question, source=source)
        result = self.engine.evaluate(input, make_features())
        assert result.is_rejected


# --- Decision Router Tests ---


class TestDecisionRouter:
    """Test decision routing logic."""

    def setup_method(self):
        self.router = DecisionRouter(ThresholdConfig())

    def test_high_confidence_high_score_passes(self):
        decision = self.router.decide(score=85.0, confidence=0.95)
        assert decision == Decision.PASS

    def test_high_confidence_low_score_rejects(self):
        decision = self.router.decide(score=20.0, confidence=0.95)
        assert decision == Decision.REJECT

    def test_low_confidence_goes_to_review(self):
        decision = self.router.decide(score=60.0, confidence=0.5)
        assert decision == Decision.REVIEW

    def test_borderline_score_goes_to_review(self):
        decision = self.router.decide(score=50.0, confidence=0.85)
        assert decision == Decision.REVIEW

    def test_needs_escalation_in_uncertain_range(self):
        assert self.router.needs_escalation(score=60.0, confidence=0.75)

    def test_no_escalation_when_confident(self):
        assert not self.router.needs_escalation(score=85.0, confidence=0.95)

    def test_no_escalation_when_very_low_confidence(self):
        # Very low confidence goes straight to review, no LLM needed
        assert not self.router.needs_escalation(score=60.0, confidence=0.5)


# --- Evaluation Engine cascade ---


class TestEvaluationEngine:
    """Test engine orchestration with mocked tiers."""

    def setup_method(self):
        self.engine = make_engine()

    async def test_tier1_reject_skips_later_tiers(self):
        scores = [make_dimension(score=30.0, confidence=0.95)]
        self.engine.tier1.evaluate.return_value = Tier1Result(
            is_rejected=True,
            quality_score=30.0,
            explanation="Rule-based rejection: too short",
            dimension_scores=scores,
        )

        result = await self.engine.evaluate(make_input(), make_features())

        assert result.decision == Decision.REJECT
        assert result.tier_used == 1
        assert result.quality_score == 30.0
        assert result.confidence == 0.95
        assert result.explanation == "Rule-based rejection: too short"
        assert result.dimension_scores == scores
        assert result.human_review_recommended is False
        self.engine.tier2.score.assert_not_called()
        self.engine.tier3.evaluate.assert_not_called()

    async def test_confident_pass_stays_at_tier2(self):
        self.engine.tier1.evaluate.return_value = Tier1Result(is_rejected=False)
        scores = [make_dimension(score=85.0, confidence=0.95)]
        self.engine.tier2.score.return_value = Tier2Result(
            quality_score=85.0,
            confidence=0.95,
            explanation="Strong on: correctness",
            dimension_scores=scores,
        )

        result = await self.engine.evaluate(make_input(), make_features())

        assert result.decision == Decision.PASS
        assert result.tier_used == 2
        assert result.quality_score == 85.0
        assert result.confidence == 0.95
        assert result.explanation == "Strong on: correctness"
        assert result.dimension_scores == scores
        assert result.human_review_recommended is False
        self.engine.tier3.evaluate.assert_not_called()

    async def test_confident_low_score_rejects_at_tier2(self):
        self.engine.tier1.evaluate.return_value = Tier1Result(is_rejected=False)
        self.engine.tier2.score.return_value = Tier2Result(
            quality_score=20.0,
            confidence=0.95,
            explanation="Weak on: correctness",
            dimension_scores=[make_dimension(score=20.0, confidence=0.95)],
        )

        result = await self.engine.evaluate(make_input(), make_features())

        assert result.decision == Decision.REJECT
        assert result.tier_used == 2
        assert result.human_review_recommended is False
        self.engine.tier3.evaluate.assert_not_called()

    async def test_low_confidence_reviews_without_tier3(self):
        self.engine.tier1.evaluate.return_value = Tier1Result(is_rejected=False)
        self.engine.tier2.score.return_value = Tier2Result(
            quality_score=60.0,
            confidence=0.5,
            explanation="Uncertain",
            dimension_scores=[make_dimension(score=60.0, confidence=0.5)],
        )

        result = await self.engine.evaluate(make_input(), make_features())

        assert result.decision == Decision.REVIEW
        assert result.tier_used == 2
        assert result.human_review_recommended is True
        self.engine.tier3.evaluate.assert_not_called()

    async def test_uncertain_confidence_escalates_and_blends(self):
        evaluation_input = make_input()
        features = make_features()
        self.engine.tier1.evaluate.return_value = Tier1Result(is_rejected=False)
        tier2_result = Tier2Result(
            quality_score=70.0,
            confidence=0.8,
            explanation="Tier 2 uncertain",
            dimension_scores=[make_dimension(score=70.0, confidence=0.8)],
        )
        tier3_scores = [make_dimension(score=90.0, confidence=0.95)]
        tier3_result = Tier3Result(
            quality_score=90.0,
            confidence=0.95,
            explanation="LLM judge: high quality",
            dimension_scores=tier3_scores,
        )
        self.engine.tier2.score.return_value = tier2_result
        self.engine.tier3.evaluate.return_value = tier3_result

        result = await self.engine.evaluate(evaluation_input, features)

        self.engine.tier3.evaluate.assert_awaited_once_with(
            evaluation_input, tier2_result
        )
        assert result.tier_used == 3
        assert result.quality_score == 84.0  # 0.3 * 70 + 0.7 * 90
        assert result.confidence == 0.95  # max(0.8, 0.95)
        assert result.explanation == "LLM judge: high quality"
        assert result.dimension_scores == tier3_scores
        assert result.decision == Decision.PASS
        assert result.human_review_recommended is False

    async def test_escalation_review_sets_human_review_flag(self):
        self.engine.tier1.evaluate.return_value = Tier1Result(is_rejected=False)
        self.engine.tier2.score.return_value = Tier2Result(
            quality_score=60.0,
            confidence=0.75,
            explanation="Tier 2 borderline",
            dimension_scores=[make_dimension(score=60.0, confidence=0.75)],
        )
        self.engine.tier3.evaluate.return_value = Tier3Result(
            quality_score=65.0,
            confidence=0.82,
            explanation="LLM judge: still unclear",
            dimension_scores=[make_dimension(score=65.0, confidence=0.82)],
        )

        result = await self.engine.evaluate(make_input(), make_features())

        assert result.tier_used == 3
        assert result.quality_score == 63.5  # 0.3 * 60 + 0.7 * 65
        assert result.confidence == 0.82
        assert result.decision == Decision.REVIEW
        assert result.human_review_recommended is True

    async def test_missing_evaluation_id_defaults_to_unknown(self):
        self.engine.tier1.evaluate.return_value = Tier1Result(
            is_rejected=True,
            quality_score=10.0,
            explanation="rejected",
            dimension_scores=[make_dimension(score=10.0, confidence=0.95)],
        )
        evaluation_input = make_input()
        evaluation_input.evaluation_id = None

        result = await self.engine.evaluate(evaluation_input, make_features())

        assert result.evaluation_id == "unknown"
