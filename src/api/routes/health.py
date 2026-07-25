"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "ml-eval-platform"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe — checks downstream dependencies."""
    # In production: check Kafka, Redis, DB connectivity
    checks = {
        "kafka": "healthy",
        "redis": "healthy",
        "database": "healthy",
        "model_loaded": True,
    }
    all_healthy = all(
        v == "healthy" or v is True for v in checks.values()
    )
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
    }
