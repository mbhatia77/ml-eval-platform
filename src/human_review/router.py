"""Human review routing and queue management.

Routes questions to appropriate reviewers based on priority,
domain expertise, and workload balancing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from src.utils.models import (
    EvaluationInput,
    EvaluationResult,
    HumanReviewTask,
)

logger = logging.getLogger(__name__)


class ReviewRouter:
    """
    Manages the human review queue.

    Responsibilities:
    - Create review tasks from evaluation results
    - Assign priority based on confidence and flags
    - Route to appropriate reviewer pool
    - Track reviewer workload and availability
    """

    # Priority levels
    P0_SAFETY = 0       # Safety flags — immediate review
    P1_HIGH = 1         # Very low confidence, new domain
    P2_NORMAL = 2       # Standard review cases
    P3_AUDIT = 3        # Random audit sample
    P4_CALIBRATION = 4  # Calibration checks

    def create_review_task(
        self,
        input: EvaluationInput,
        result: EvaluationResult,
    ) -> HumanReviewTask:
        """Create a human review task from an evaluation result."""
        priority = self._compute_priority(result)
        deadline = self._compute_deadline(priority)

        task = HumanReviewTask(
            task_id=f"review-{result.evaluation_id}",
            evaluation_id=result.evaluation_id,
            input=input,
            automated_result=result,
            priority=priority,
            deadline=deadline,
        )

        logger.info(
            f"Created review task {task.task_id} "
            f"(priority={priority}, deadline={deadline})"
        )
        return task

    def _compute_priority(self, result: EvaluationResult) -> int:
        """Determine review priority based on evaluation signals."""
        # Safety concerns get highest priority
        safety_scores = [
            s for s in result.dimension_scores
            if s.dimension.value == "bias_safety"
        ]
        if safety_scores and safety_scores[0].score < 50:
            return self.P0_SAFETY

        # Very low confidence → high priority
        if result.confidence < 0.5:
            return self.P1_HIGH

        # Standard review
        return self.P2_NORMAL

    def _compute_deadline(self, priority: int) -> datetime:
        """Set deadline based on priority."""
        deadlines = {
            self.P0_SAFETY: timedelta(hours=1),
            self.P1_HIGH: timedelta(hours=4),
            self.P2_NORMAL: timedelta(hours=24),
            self.P3_AUDIT: timedelta(hours=48),
            self.P4_CALIBRATION: timedelta(hours=72),
        }
        delta = deadlines.get(priority, timedelta(hours=24))
        return datetime.utcnow() + delta

    async def assign_reviewer(self, task: HumanReviewTask) -> Optional[str]:
        """
        Assign a reviewer to a task based on:
        - Domain expertise match
        - Current workload
        - Availability
        - Historical agreement rate
        """
        # In production: query reviewer pool, check availability,
        # match domain expertise, balance workload
        return None

    async def enqueue(self, task: HumanReviewTask) -> None:
        """Add task to the review queue (Redis Streams)."""
        # In production:
        # await redis.xadd(
        #     f"review-queue:{task.priority}",
        #     {"task": task.model_dump_json()}
        # )
        pass
