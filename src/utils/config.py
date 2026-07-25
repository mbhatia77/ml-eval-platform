"""Application configuration management."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class KafkaConfig(BaseSettings):
    """Kafka connection settings."""
    bootstrap_servers: str = "localhost:9092"
    evaluation_topic: str = "evaluation-requests"
    scoring_topic: str = "scoring-results"
    feedback_topic: str = "feedback-events"
    consumer_group: str = "eval-platform"
    num_partitions: int = 32

    class Config:
        env_prefix = "KAFKA_"


class RedisConfig(BaseSettings):
    """Redis feature store settings."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    feature_ttl_seconds: int = 86400  # 24 hours
    password: str = ""

    class Config:
        env_prefix = "REDIS_"


class DatabaseConfig(BaseSettings):
    """PostgreSQL settings."""
    host: str = "localhost"
    port: int = 5432
    database: str = "eval_platform"
    user: str = "eval_user"
    password: str = ""
    pool_size: int = 20

    class Config:
        env_prefix = "DB_"


class ModelConfig(BaseSettings):
    """Model inference settings."""
    tier2_model_path: str = "models/deberta-v3-eval"
    tier2_xgboost_path: str = "models/xgboost-features"
    tier3_provider: str = "openai"  # openai | anthropic
    tier3_model: str = "gpt-4"
    tier3_max_tokens: int = 1024
    tier3_temperature: float = 0.1
    batch_size: int = 32
    max_concurrent_llm_calls: int = 10

    class Config:
        env_prefix = "MODEL_"


class ThresholdConfig(BaseSettings):
    """Decision routing thresholds."""
    pass_score_min: float = 75.0
    pass_confidence_min: float = 0.9
    reject_score_max: float = 30.0
    reject_confidence_min: float = 0.9
    review_confidence_max: float = 0.7
    tier3_confidence_min: float = 0.7
    tier3_confidence_max: float = 0.9

    class Config:
        env_prefix = "THRESHOLD_"


class AppConfig(BaseSettings):
    """Top-level application configuration."""
    app_name: str = "ml-eval-platform"
    environment: str = "development"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    workers: int = 4

    kafka: KafkaConfig = KafkaConfig()
    redis: RedisConfig = RedisConfig()
    database: DatabaseConfig = DatabaseConfig()
    model: ModelConfig = ModelConfig()
    thresholds: ThresholdConfig = ThresholdConfig()

    class Config:
        env_prefix = "APP_"


def get_config() -> AppConfig:
    """Load configuration from environment variables."""
    return AppConfig()
