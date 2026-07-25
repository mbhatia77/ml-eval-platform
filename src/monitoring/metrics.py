"""Prometheus metrics for the evaluation platform.

Tracks latency, throughput, decision distributions,
model performance, and business metrics.
"""

from __future__ import annotations

from enum import Enum

# In production: from prometheus_client import Counter, Histogram, Gauge, Summary


class MetricNames(str, Enum):
    """Metric names for the evaluation platform."""
    # Throughput
    EVALUATIONS_TOTAL = "evaluations_total"
    EVALUATIONS_BY_DECISION = "evaluations_by_decision"
    EVALUATIONS_BY_TIER = "evaluations_by_tier"

    # Latency
    EVALUATION_LATENCY = "evaluation_latency_seconds"
    FEATURE_EXTRACTION_LATENCY = "feature_extraction_latency_seconds"
    TIER1_LATENCY = "tier1_latency_seconds"
    TIER2_LATENCY = "tier2_latency_seconds"
    TIER3_LATENCY = "tier3_latency_seconds"

    # Quality
    QUALITY_SCORE_DISTRIBUTION = "quality_score"
    CONFIDENCE_DISTRIBUTION = "confidence_score"

    # Human Review
    REVIEW_QUEUE_SIZE = "review_queue_size"
    REVIEW_LATENCY = "human_review_latency_seconds"
    REVIEWER_AGREEMENT_RATE = "reviewer_agreement_rate"

    # Model
    MODEL_PREDICTION_DRIFT = "model_prediction_drift"
    FEATURE_DRIFT = "feature_distribution_drift"

    # Business
    HUMAN_ACCEPTANCE_RATE = "human_acceptance_rate"
    FALSE_ACCEPTANCE_RATE = "false_acceptance_rate"
    COST_PER_EVALUATION = "cost_per_evaluation"


class MetricsCollector:
    """
    Collects and exports platform metrics.

    In production, this wraps prometheus_client metrics.
    Metrics are scraped by Prometheus and visualized in Grafana.
    """

    def __init__(self):
        # In production: initialize Prometheus metrics
        # self.eval_counter = Counter(
        #     MetricNames.EVALUATIONS_TOTAL,
        #     "Total evaluations processed",
        #     ["decision", "tier", "domain"]
        # )
        # self.latency_histogram = Histogram(
        #     MetricNames.EVALUATION_LATENCY,
        #     "Evaluation latency in seconds",
        #     buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        # )
        pass

    def record_evaluation(
        self,
        decision: str,
        tier: int,
        domain: str,
        latency_ms: float,
        quality_score: float,
        confidence: float,
    ) -> None:
        """Record metrics for a completed evaluation."""
        # self.eval_counter.labels(decision=decision, tier=tier, domain=domain).inc()
        # self.latency_histogram.observe(latency_ms / 1000.0)
        pass

    def record_human_review(
        self,
        wait_time_seconds: float,
        agreed_with_model: bool,
    ) -> None:
        """Record metrics for a completed human review."""
        pass

    def record_queue_size(self, size: int) -> None:
        """Update the current review queue size gauge."""
        pass
