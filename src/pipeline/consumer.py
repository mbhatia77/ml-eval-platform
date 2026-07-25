"""Kafka consumer for processing evaluation requests.

Consumes from the evaluation topic, orchestrates feature extraction
and evaluation, then publishes results.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from src.utils.config import AppConfig, get_config
from src.utils.models import EvaluationInput, QuestionMetadata
from src.evaluation.engine import EvaluationEngine
from src.features.extractor import FeatureExtractor
from src.features.store import FeatureStore

logger = logging.getLogger(__name__)


class EvaluationConsumer:
    """
    Kafka consumer that processes evaluation requests.

    Consumes messages from the evaluation topic, extracts features,
    runs the evaluation engine, and publishes results.
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.feature_extractor = FeatureExtractor()
        self.feature_store = FeatureStore(self.config.redis)
        self.evaluation_engine = EvaluationEngine(self.config)
        self.running = False

    async def start(self):
        """Start consuming messages."""
        self.running = True
        logger.info(
            f"Starting evaluation consumer on topic: "
            f"{self.config.kafka.evaluation_topic}"
        )

        # In production:
        # from aiokafka import AIOKafkaConsumer
        # consumer = AIOKafkaConsumer(
        #     self.config.kafka.evaluation_topic,
        #     bootstrap_servers=self.config.kafka.bootstrap_servers,
        #     group_id=self.config.kafka.consumer_group,
        #     auto_offset_reset='earliest',
        #     value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        # )
        # await consumer.start()
        # async for message in consumer:
        #     await self.process_message(message.value)

        logger.info("Consumer started (placeholder mode)")

    async def stop(self):
        """Stop the consumer gracefully."""
        self.running = False
        logger.info("Consumer stopping...")

    async def process_message(self, message: dict) -> None:
        """
        Process a single evaluation request.

        Steps:
        1. Deserialize the evaluation input
        2. Extract features
        3. Store features in feature store
        4. Run evaluation engine
        5. Store and publish result
        """
        try:
            # Deserialize input
            input = EvaluationInput(**message)

            # Extract features
            features = await self.feature_extractor.extract(input)

            # Store features
            await self.feature_store.store(features)
            await self.feature_store.store_offline(features)

            # Run evaluation
            result = await self.evaluation_engine.evaluate(input, features)

            # Store result
            await self._store_result(result)

            # Publish result event
            await self._publish_result(result)

            logger.info(
                f"Evaluated {result.evaluation_id}: "
                f"score={result.quality_score}, "
                f"decision={result.decision.value}, "
                f"tier={result.tier_used}, "
                f"latency={result.latency_ms:.1f}ms"
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._send_to_dlq(message, str(e))

    async def _store_result(self, result) -> None:
        """Store evaluation result in the database."""
        # In production: INSERT into PostgreSQL
        pass

    async def _publish_result(self, result) -> None:
        """Publish result to the results Kafka topic."""
        # In production: produce to scoring_topic
        pass

    async def _send_to_dlq(self, message: dict, error: str) -> None:
        """Send failed message to dead letter queue."""
        # In production: write to S3 DLQ with error context
        logger.warning(f"Message sent to DLQ: {error}")


async def main():
    """Entry point for running the consumer."""
    config = get_config()
    consumer = EvaluationConsumer(config)

    try:
        await consumer.start()
    except KeyboardInterrupt:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
