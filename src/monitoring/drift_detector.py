"""Drift detection for model and data monitoring.

Detects concept drift, data drift, and prediction drift
to trigger model retraining when performance degrades.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class DriftType(str, Enum):
    """Types of drift the system monitors."""
    DATA_DRIFT = "data_drift"           # Input distribution changed
    CONCEPT_DRIFT = "concept_drift"     # Relationship between input/output changed
    PREDICTION_DRIFT = "prediction_drift"  # Output distribution changed
    LABEL_DRIFT = "label_drift"         # Human feedback distribution changed


@dataclass
class DriftAlert:
    """Alert generated when drift is detected."""
    drift_type: DriftType
    severity: str  # low | medium | high | critical
    metric_name: str
    current_value: float
    baseline_value: float
    threshold: float
    message: str
    should_retrain: bool = False


class DriftDetector:
    """
    Monitors for various types of drift.

    Uses statistical tests to compare recent data against
    baseline distributions. Triggers alerts and retraining
    when significant drift is detected.
    """

    # KL-divergence thresholds
    DATA_DRIFT_THRESHOLD = 0.1
    PREDICTION_DRIFT_THRESHOLD = 0.15
    PERFORMANCE_DROP_THRESHOLD = 0.02  # 2% F1 drop

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.baseline_scores: list[float] = []
        self.recent_scores: list[float] = []
        self.baseline_confidence: list[float] = []
        self.recent_confidence: list[float] = []

    def check_prediction_drift(
        self,
        recent_scores: list[float],
        baseline_scores: list[float],
    ) -> Optional[DriftAlert]:
        """Check if score distribution has shifted."""
        if len(recent_scores) < self.window_size:
            return None

        # KL-divergence between distributions
        kl_div = self._compute_kl_divergence(recent_scores, baseline_scores)

        if kl_div > self.PREDICTION_DRIFT_THRESHOLD:
            return DriftAlert(
                drift_type=DriftType.PREDICTION_DRIFT,
                severity="high" if kl_div > 0.3 else "medium",
                metric_name="score_distribution_kl",
                current_value=kl_div,
                baseline_value=0.0,
                threshold=self.PREDICTION_DRIFT_THRESHOLD,
                message=f"Prediction drift detected (KL={kl_div:.3f})",
                should_retrain=kl_div > 0.3,
            )

        return None

    def check_performance_drift(
        self,
        recent_f1: float,
        baseline_f1: float,
    ) -> Optional[DriftAlert]:
        """Check if model performance has degraded."""
        drop = baseline_f1 - recent_f1

        if drop > self.PERFORMANCE_DROP_THRESHOLD:
            return DriftAlert(
                drift_type=DriftType.CONCEPT_DRIFT,
                severity="critical" if drop > 0.05 else "high",
                metric_name="f1_score_drop",
                current_value=recent_f1,
                baseline_value=baseline_f1,
                threshold=self.PERFORMANCE_DROP_THRESHOLD,
                message=f"Performance degradation: F1 dropped by {drop:.3f}",
                should_retrain=True,
            )

        return None

    def check_label_drift(
        self,
        recent_acceptance_rate: float,
        baseline_acceptance_rate: float,
    ) -> Optional[DriftAlert]:
        """Check if human acceptance rate has changed significantly."""
        change = abs(recent_acceptance_rate - baseline_acceptance_rate)

        if change > 0.05:  # 5% change in acceptance rate
            return DriftAlert(
                drift_type=DriftType.LABEL_DRIFT,
                severity="medium",
                metric_name="human_acceptance_rate_change",
                current_value=recent_acceptance_rate,
                baseline_value=baseline_acceptance_rate,
                threshold=0.05,
                message=f"Human acceptance rate shifted by {change:.1%}",
                should_retrain=change > 0.1,
            )

        return None

    def _compute_kl_divergence(
        self,
        p_samples: list[float],
        q_samples: list[float],
    ) -> float:
        """Compute KL-divergence between two sample distributions."""
        # Discretize into histogram bins
        bins = np.linspace(0, 100, 21)  # 20 bins from 0-100
        p_hist, _ = np.histogram(p_samples, bins=bins, density=True)
        q_hist, _ = np.histogram(q_samples, bins=bins, density=True)

        # Add smoothing to avoid log(0)
        epsilon = 1e-10
        p_hist = p_hist + epsilon
        q_hist = q_hist + epsilon

        # Normalize
        p_hist = p_hist / p_hist.sum()
        q_hist = q_hist / q_hist.sum()

        # KL-divergence
        kl = np.sum(p_hist * np.log(p_hist / q_hist))
        return float(kl)
