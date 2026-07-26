"""Feature store interface for online and offline feature access."""

from __future__ import annotations

import logging
from typing import Optional

from src.utils.config import RedisConfig
from src.utils.models import FeatureVector

logger = logging.getLogger(__name__)


class FeatureStore:
    """
    Two-layer feature store:
    - Online (Redis): low-latency serving for real-time evaluation
    - Offline (PostgreSQL/Parquet): historical features for training

    Features are keyed by evaluation_id with a 24-hour TTL.
    """

    def __init__(self, config: RedisConfig):
        self.config = config
        self.redis_client = None  # Initialized on connect
        self._connect()

    def _connect(self):
        """Connect to Redis."""
        # In production:
        # import redis.asyncio as redis
        # self.redis_client = redis.Redis(
        #     host=self.config.host,
        #     port=self.config.port,
        #     db=self.config.db,
        #     password=self.config.password,
        # )
        logger.info("Feature store connected (placeholder mode)")

    async def store(self, features: FeatureVector) -> None:
        """Store computed features in the online store."""
        # In production:
        # key = f"features:{features.evaluation_id}"
        # value = json.dumps({
        #     "text_features": features.text_features,
        #     "semantic_features": features.semantic_features,
        #     "reference_features": features.reference_features,
        #     "safety_features": features.safety_features,
        #     "duplicate_features": features.duplicate_features,
        # })
        # await self.redis_client.setex(key, self.config.feature_ttl_seconds, value)
        logger.debug(f"Stored features for {features.evaluation_id}")

    async def get(self, evaluation_id: str) -> Optional[FeatureVector]:
        """Retrieve features from the online store."""
        # In production:
        # value = await self.redis_client.get(key)
        # if value is None:
        #     return None
        # data = json.loads(value)
        # return FeatureVector(evaluation_id=evaluation_id, **data)

        return None

    async def store_offline(self, features: FeatureVector) -> None:
        """Store features in the offline store for training."""
        # In production: write to PostgreSQL or Parquet files
        # Used for point-in-time correct feature joins during training
        pass
