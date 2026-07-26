"""Tier 1: Rule-based evaluation engine.

Fast, deterministic checks that catch obvious quality failures
without any model inference. Runs in < 10ms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.utils.models import (
    DimensionScore,
    EvaluationDimension,
    EvaluationInput,
    FeatureVector,
)


@dataclass
class Tier1Result:
    """Result from rule-based evaluation."""
    is_rejected: bool = False
    quality_score: float = 0.0
    confidence: float = 0.95
    explanation: str = ""
    dimension_scores: list[DimensionScore] = field(default_factory=list)


class Tier1RuleEngine:
    """
    Rule-based evaluator for catching obvious failures.

    Checks:
    - Question format (ends with ?, minimum length)
    - Grammar basics (capitalization, basic structure)
    - Length constraints (too short or too long)
    - Duplication with source (verbatim copy detection)
    - Safety signals (explicit blocklist)
    """

    # Minimum acceptable question length (characters)
    MIN_QUESTION_LENGTH = 15
    MAX_QUESTION_LENGTH = 500
    MIN_ANSWER_LENGTH = 5

    # Patterns that indicate low quality
    BLOCKLIST_PATTERNS = [
        r"(?i)\b(test|todo|fixme|placeholder)\b",
        r"^(question|q):?\s*$",
    ]

    def evaluate(self, input: EvaluationInput, features: FeatureVector) -> Tier1Result:
        """Run all rule-based checks."""
        failures: list[str] = []
        scores: list[DimensionScore] = []

        # Check: Question format
        grammar_score = self._check_grammar_format(input.generated_question, failures)
        scores.append(DimensionScore(
            dimension=EvaluationDimension.GRAMMAR,
            score=grammar_score,
            confidence=0.95,
        ))

        # Check: Length constraints
        clarity_score = self._check_length(input, failures)
        scores.append(DimensionScore(
            dimension=EvaluationDimension.CLARITY,
            score=clarity_score,
            confidence=0.95,
        ))

        # Check: Verbatim copy from source
        groundedness_score = self._check_verbatim_copy(input, failures)
        scores.append(DimensionScore(
            dimension=EvaluationDimension.GROUNDEDNESS,
            score=groundedness_score,
            confidence=0.90,
        ))

        # Check: Safety blocklist
        safety_score = self._check_safety(input.generated_question, failures)
        scores.append(DimensionScore(
            dimension=EvaluationDimension.BIAS_SAFETY,
            score=safety_score,
            confidence=0.95,
        ))

        # Determine result
        if failures:
            return Tier1Result(
                is_rejected=True,
                quality_score=min(s.score for s in scores),
                explanation=f"Rule-based rejection: {'; '.join(failures)}",
                dimension_scores=scores,
            )

        # Compute aggregate score for passing questions
        avg_score = sum(s.score for s in scores) / len(scores) if scores else 50.0
        return Tier1Result(
            is_rejected=False,
            quality_score=avg_score,
            explanation="Passed rule-based checks",
            dimension_scores=scores,
        )

    def _check_grammar_format(self, question: str, failures: list[str]) -> float:
        """Check basic grammar and formatting rules."""
        score = 100.0

        # Must end with question mark
        if not question.strip().endswith("?"):
            failures.append("Question does not end with '?'")
            score -= 50.0

        # Must start with capital letter
        if question and not question[0].isupper():
            score -= 20.0

        # Check for blocklist patterns
        for pattern in self.BLOCKLIST_PATTERNS:
            if re.search(pattern, question):
                failures.append("Contains blocklisted pattern")
                score -= 40.0
                break

        return max(score, 0.0)

    def _check_length(self, input: EvaluationInput, failures: list[str]) -> float:
        """Check length constraints."""
        q_len = len(input.generated_question.strip())
        a_len = len(input.expected_answer.strip())

        if q_len < self.MIN_QUESTION_LENGTH:
            failures.append(f"Question too short ({q_len} chars)")
            return 10.0

        if q_len > self.MAX_QUESTION_LENGTH:
            failures.append(f"Question too long ({q_len} chars)")
            return 30.0

        if a_len < self.MIN_ANSWER_LENGTH:
            failures.append(f"Answer too short ({a_len} chars)")
            return 20.0

        return 100.0

    def _check_verbatim_copy(self, input: EvaluationInput, failures: list[str]) -> float:
        """Check if question is a verbatim copy from source document."""
        question_lower = input.generated_question.lower().strip().rstrip("?")
        source_lower = input.source_document.lower()

        # If the entire question (minus punctuation) appears verbatim in source
        if question_lower in source_lower and len(question_lower) > 30:
            failures.append("Question is verbatim copy from source")
            return 5.0

        return 85.0  # Neutral — detailed check happens in Tier 2

    def _check_safety(self, question: str, failures: list[str]) -> float:
        """Basic safety check using blocklist patterns."""
        # In production: integrate with a proper content moderation API
        # This is a minimal rule-based check
        safety_patterns = [
            r"(?i)\b(kill|harm|weapon|illegal|hack)\b.*\b(how|instructions|steps)\b",
        ]

        for pattern in safety_patterns:
            if re.search(pattern, question):
                failures.append("Safety concern detected")
                return 0.0

        return 100.0
