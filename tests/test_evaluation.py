"""Tests for the evaluation engine."""

import pytest
from src.utils.models import (
    Decision,
    EvaluationDimension,
    EvaluationInput,
    FeatureVector,
    QuestionMetadata,
    DocumentType,
)
from src.evaluation.tier1_rules import Tier1RuleEngine
from src.evaluation.decision_router import DecisionRouter
from src.utils.config import ThresholdConfig


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
