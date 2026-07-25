"""Evaluation API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.utils.models import (
    Decision,
    EvaluationInput,
    EvaluationResult,
)

router = APIRouter()


class EvaluationRequest(BaseModel):
    """Request body for single question evaluation."""
    source_document: str
    generated_question: str
    expected_answer: str
    metadata: dict


class EvaluationResponse(BaseModel):
    """Async evaluation acceptance response."""
    evaluation_id: str
    status: str = "accepted"
    message: str = "Evaluation queued for processing"


class EvaluationStatusResponse(BaseModel):
    """Status of an evaluation."""
    evaluation_id: str
    status: str  # pending | processing | completed | failed
    result: EvaluationResult | None = None


@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_evaluation(request: EvaluationRequest):
    """
    Submit a question for evaluation.

    The question is validated and queued for async processing.
    Use the returned evaluation_id to poll for results.
    """
    evaluation_id = str(uuid.uuid4())

    # Validate input
    if not request.source_document.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_document cannot be empty",
        )
    if not request.generated_question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="generated_question cannot be empty",
        )

    # In production: publish to Kafka evaluation topic
    # await kafka_producer.send(config.kafka.evaluation_topic, message)

    return EvaluationResponse(evaluation_id=evaluation_id)


@router.get(
    "/evaluate/{evaluation_id}",
    response_model=EvaluationStatusResponse,
)
async def get_evaluation_status(evaluation_id: str):
    """
    Get the status and result of an evaluation.

    Returns the current status and, if completed, the full evaluation result.
    """
    # In production: query results database
    # result = await db.get_evaluation(evaluation_id)

    # Placeholder response
    return EvaluationStatusResponse(
        evaluation_id=evaluation_id,
        status="pending",
        result=None,
    )


@router.post("/evaluate/sync")
async def evaluate_sync(request: EvaluationRequest):
    """
    Synchronous evaluation endpoint for low-volume, latency-tolerant use cases.

    Runs the full evaluation pipeline inline and returns the result.
    Not recommended for production traffic — use async endpoint instead.
    """
    evaluation_id = str(uuid.uuid4())

    # In production: run evaluation pipeline directly
    # result = await evaluation_engine.evaluate(input)

    # Placeholder
    from src.utils.models import DimensionScore, EvaluationDimension

    placeholder_result = EvaluationResult(
        evaluation_id=evaluation_id,
        quality_score=75.0,
        confidence=0.85,
        decision=Decision.PASS,
        dimension_scores=[
            DimensionScore(
                dimension=EvaluationDimension.CORRECTNESS,
                score=80.0,
                confidence=0.9,
            )
        ],
        explanation="Placeholder evaluation",
        human_review_recommended=False,
        tier_used=2,
        latency_ms=0.0,
        model_version="v0.1.0",
    )

    return placeholder_result
