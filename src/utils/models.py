"""Core data models used across the platform."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Type of source document."""
    MANUAL = "manual"
    REGULATION = "regulation"
    KNOWLEDGE_BASE = "knowledge_base"
    POLICY = "policy"
    TECHNICAL = "technical"
    GENERAL = "general"


class Decision(str, Enum):
    """Evaluation decision for a question."""
    PASS = "pass"
    REVIEW = "review"
    REJECT = "reject"


class EvaluationDimension(str, Enum):
    """Quality dimensions for evaluation."""
    CORRECTNESS = "correctness"
    GROUNDEDNESS = "groundedness"
    RELEVANCE = "relevance"
    DIFFICULTY = "difficulty"
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    NON_DUPLICATION = "non_duplication"
    HALLUCINATION = "hallucination"
    BIAS_SAFETY = "bias_safety"
    GRAMMAR = "grammar"


class QuestionMetadata(BaseModel):
    """Metadata associated with a generated question."""
    document_type: DocumentType
    domain: str
    language: str = "en"
    generation_model: str
    prompt_version: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None


class EvaluationInput(BaseModel):
    """Input to the evaluation pipeline."""
    evaluation_id: Optional[str] = None
    source_document: str
    generated_question: str
    expected_answer: str
    metadata: QuestionMetadata


class DimensionScore(BaseModel):
    """Score for a single evaluation dimension."""
    dimension: EvaluationDimension
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    explanation: Optional[str] = None


class EvaluationResult(BaseModel):
    """Complete evaluation result for a question."""
    evaluation_id: str
    quality_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    decision: Decision
    dimension_scores: list[DimensionScore]
    explanation: str
    human_review_recommended: bool
    tier_used: int = Field(ge=1, le=3, description="Highest tier used for evaluation")
    latency_ms: float
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    model_version: str = "v0.1.0"


class HumanReviewTask(BaseModel):
    """A task assigned to a human reviewer."""
    task_id: str
    evaluation_id: str
    input: EvaluationInput
    automated_result: EvaluationResult
    priority: int = Field(ge=0, le=4, description="0=highest, 4=lowest")
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None


class HumanReviewResponse(BaseModel):
    """Response from a human reviewer."""
    task_id: str
    reviewer_id: str
    decision: Decision
    dimension_scores: list[DimensionScore]
    feedback: Optional[str] = None
    time_spent_seconds: float
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureVector(BaseModel):
    """Computed features for a question."""
    evaluation_id: str
    text_features: dict[str, float]
    semantic_features: dict[str, float]
    reference_features: dict[str, float]
    safety_features: dict[str, float]
    duplicate_features: dict[str, float]
    computed_at: datetime = Field(default_factory=datetime.utcnow)
