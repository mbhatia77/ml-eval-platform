"""Batch evaluation endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class BatchRequest(BaseModel):
    """Request to start a batch evaluation."""
    s3_input_path: str
    callback_url: str | None = None
    priority: int = 2


class BatchResponse(BaseModel):
    """Response for batch submission."""
    batch_id: str
    status: str = "accepted"
    estimated_duration_minutes: int
    message: str


class BatchStatus(BaseModel):
    """Current status of a batch evaluation."""
    batch_id: str
    status: str  # accepted | processing | completed | failed
    total_questions: int
    processed: int
    passed: int
    reviewed: int
    rejected: int
    progress_percent: float
    results_path: str | None = None


@router.post(
    "/batch/evaluate",
    response_model=BatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_batch(request: BatchRequest):
    """
    Submit a batch of questions for evaluation.

    Accepts an S3 path to a JSONL file containing questions.
    Each line should be a valid EvaluationInput JSON object.
    """
    batch_id = str(uuid.uuid4())

    # In production:
    # 1. Validate S3 path exists and is accessible
    # 2. Count lines to estimate duration
    # 3. Trigger Airflow DAG

    estimated_minutes = 15  # Placeholder

    return BatchResponse(
        batch_id=batch_id,
        estimated_duration_minutes=estimated_minutes,
        message=f"Batch evaluation queued. Check status at /api/v1/batch/{batch_id}",
    )


@router.get("/batch/{batch_id}", response_model=BatchStatus)
async def get_batch_status(batch_id: str):
    """Get the current status of a batch evaluation."""
    # In production: query batch status from DB

    return BatchStatus(
        batch_id=batch_id,
        status="processing",
        total_questions=0,
        processed=0,
        passed=0,
        reviewed=0,
        rejected=0,
        progress_percent=0.0,
    )
