"""Feedback collection and processing.

Collects human review decisions, handles disagreements,
and prepares labeled data for model retraining.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.utils.models import Decision, HumanReviewResponse

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Collects and processes human review feedback.

    Handles:
    - Single reviewer responses
    - Multi-reviewer agreement checks
    - Disagreement escalation
    - Gold dataset additions
    - Reviewer reliability scoring
    """

    # Minimum reviewers for gold dataset addition
    MIN_REVIEWERS_FOR_GOLD = 3
    # Agreement threshold for auto-acceptance
    AGREEMENT_THRESHOLD = 0.67  # 2 out of 3

    async def submit_review(self, response: HumanReviewResponse) -> dict:
        """
        Process a submitted review.

        Returns status indicating if more reviews are needed.
        """
        # Store the review
        await self._store_review(response)

        # Check if we have enough reviews for this question
        all_reviews = await self._get_reviews(response.task_id)

        if len(all_reviews) >= 2:
            agreement = self._check_agreement(all_reviews)
            if agreement["agreed"]:
                await self._finalize_decision(response.task_id, agreement)
                return {"status": "finalized", "decision": agreement["decision"]}
            elif len(all_reviews) >= 3:
                # Three reviews with no agreement → escalate
                await self._escalate_to_adjudicator(response.task_id)
                return {"status": "escalated"}

        return {"status": "pending", "reviews_so_far": len(all_reviews)}

    def _check_agreement(self, reviews: list[HumanReviewResponse]) -> dict:
        """Check if reviewers agree on the decision."""
        decisions = [r.decision for r in reviews]
        from collections import Counter
        counts = Counter(decisions)
        most_common_decision, count = counts.most_common(1)[0]

        agreed = count / len(decisions) >= self.AGREEMENT_THRESHOLD
        return {
            "agreed": agreed,
            "decision": most_common_decision.value if agreed else None,
            "agreement_ratio": count / len(decisions),
            "votes": dict(counts),
        }

    async def _finalize_decision(self, task_id: str, agreement: dict) -> None:
        """Finalize the review decision and add to training data."""
        logger.info(
            f"Finalized review {task_id}: "
            f"decision={agreement['decision']}, "
            f"agreement={agreement['agreement_ratio']:.0%}"
        )
        # In production:
        # 1. Update evaluation result in DB with human decision
        # 2. Add to training dataset if agreement is high
        # 3. Update reviewer reliability scores
        # 4. Publish feedback event to Kafka

    async def _escalate_to_adjudicator(self, task_id: str) -> None:
        """Escalate disagreed reviews to a senior adjudicator."""
        logger.info(f"Escalating review {task_id} to adjudication")
        # In production: assign to senior reviewer pool

    async def _store_review(self, response: HumanReviewResponse) -> None:
        """Store a review in the database."""
        # In production: INSERT into reviews table
        pass

    async def _get_reviews(self, task_id: str) -> list[HumanReviewResponse]:
        """Get all reviews for a task."""
        # In production: SELECT from reviews WHERE task_id = ?
        return []

    async def update_reviewer_score(self, reviewer_id: str) -> None:
        """Update reviewer reliability based on agreement with majority."""
        # Track: agreement rate, speed, consistency
        pass
