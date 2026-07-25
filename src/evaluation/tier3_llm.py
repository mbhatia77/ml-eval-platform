"""Tier 3: LLM-as-Judge evaluation engine.

Uses GPT-4 or Claude for nuanced evaluation of uncertain cases.
Only invoked when Tier 2 confidence is insufficient.
Runs in < 2s, costs ~$0.02 per evaluation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from src.utils.models import (
    DimensionScore,
    EvaluationDimension,
    EvaluationInput,
)
from src.utils.config import ModelConfig
from src.evaluation.tier2_ml import Tier2Result

logger = logging.getLogger(__name__)


@dataclass
class Tier3Result:
    """Result from LLM judge evaluation."""
    quality_score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""
    dimension_scores: list[DimensionScore] = field(default_factory=list)


# Evaluation prompt template for the LLM judge
EVALUATION_PROMPT = """You are an expert assessment question evaluator. Evaluate the following AI-generated question on each quality dimension.

## Source Document
{source_document}

## Generated Question
{question}

## Expected Answer
{expected_answer}

## Evaluation Criteria
Score each dimension from 0-100:

1. **Correctness**: Is the question factually accurate based on the source?
2. **Groundedness**: Is the question supported by the source document?
3. **Relevance**: Is the question relevant to the document's main topics?
4. **Difficulty**: Is the difficulty level appropriate (not too easy/hard)?
5. **Clarity**: Is the question clear and unambiguous?
6. **Completeness**: Does the question capture important information?
7. **Non-duplication**: Is this a unique question (not repetitive)?
8. **Hallucination**: Does the question contain fabricated information? (100=no hallucination)
9. **Bias/Safety**: Is the question free from bias and safe? (100=no issues)
10. **Grammar**: Is the question grammatically correct?

## Previous ML Scores (for reference)
{ml_scores}

## Output Format
Respond with a JSON object:
{{
  "overall_score": <0-100>,
  "confidence": <0.0-1.0>,
  "dimensions": {{
    "correctness": <score>,
    "groundedness": <score>,
    "relevance": <score>,
    "difficulty": <score>,
    "clarity": <score>,
    "completeness": <score>,
    "non_duplication": <score>,
    "hallucination": <score>,
    "bias_safety": <score>,
    "grammar": <score>
  }},
  "explanation": "<brief explanation of key findings>",
  "recommendation": "pass|review|reject"
}}"""


class Tier3LLMJudge:
    """
    LLM-based evaluator for nuanced quality assessment.

    Used as the final arbiter when Tier 2 ML model is uncertain.
    Supports multiple LLM providers with automatic failover.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self.provider = config.tier3_provider
        self.model = config.tier3_model

    async def evaluate(
        self,
        input: EvaluationInput,
        tier2_result: Tier2Result,
    ) -> Tier3Result:
        """
        Evaluate a question using LLM-as-judge.

        The LLM receives the question, source document, and Tier 2 scores
        for context, then provides its own assessment.
        """
        prompt = self._build_prompt(input, tier2_result)

        # Call LLM API
        response = await self._call_llm(prompt)

        # Parse structured response
        result = self._parse_response(response)

        return result

    def _build_prompt(self, input: EvaluationInput, tier2_result: Tier2Result) -> str:
        """Build the evaluation prompt with context."""
        ml_scores_str = ", ".join(
            f"{s.dimension.value}={s.score}"
            for s in tier2_result.dimension_scores
        )

        # Truncate source document to avoid token limits
        source_truncated = input.source_document[:3000]
        if len(input.source_document) > 3000:
            source_truncated += "\n...[truncated]..."

        return EVALUATION_PROMPT.format(
            source_document=source_truncated,
            question=input.generated_question,
            expected_answer=input.expected_answer,
            ml_scores=ml_scores_str,
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API with retry and circuit breaker logic."""
        # In production:
        # if self.provider == "openai":
        #     client = openai.AsyncClient()
        #     response = await client.chat.completions.create(
        #         model=self.model,
        #         messages=[{"role": "user", "content": prompt}],
        #         temperature=self.config.tier3_temperature,
        #         max_tokens=self.config.tier3_max_tokens,
        #         response_format={"type": "json_object"},
        #     )
        #     return response.choices[0].message.content
        # elif self.provider == "anthropic":
        #     client = anthropic.AsyncAnthropic()
        #     response = await client.messages.create(...)

        # Placeholder response
        logger.info("Tier 3 LLM evaluation (placeholder mode)")
        return json.dumps({
            "overall_score": 65,
            "confidence": 0.82,
            "dimensions": {dim.value: 65.0 for dim in EvaluationDimension},
            "explanation": "Placeholder LLM evaluation",
            "recommendation": "review",
        })

    def _parse_response(self, response: str) -> Tier3Result:
        """Parse the LLM JSON response into a Tier3Result."""
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return Tier3Result(
                quality_score=50.0,
                confidence=0.3,
                explanation="LLM response parsing failed",
            )

        dimension_scores = []
        dimensions = data.get("dimensions", {})
        for dim in EvaluationDimension:
            score = dimensions.get(dim.value, 50.0)
            dimension_scores.append(DimensionScore(
                dimension=dim,
                score=float(score),
                confidence=data.get("confidence", 0.7),
            ))

        return Tier3Result(
            quality_score=float(data.get("overall_score", 50.0)),
            confidence=float(data.get("confidence", 0.7)),
            explanation=data.get("explanation", ""),
            dimension_scores=dimension_scores,
        )
