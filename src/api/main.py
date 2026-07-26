"""FastAPI application for the ML Evaluation Platform."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import batch, evaluation, health
from src.utils.config import get_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    config = get_config()
    app.state.config = config
    # Initialize connections (Kafka producer, Redis, DB pool)
    # These would be initialized here in production
    yield
    # Cleanup connections on shutdown


app = FastAPI(
    title="ML Evaluation Platform",
    description="Automated quality evaluation for AI-generated assessment questions",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(evaluation.router, prefix="/api/v1", tags=["evaluation"])
app.include_router(batch.router, prefix="/api/v1", tags=["batch"])


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "src.api.main:app",
        host=config.api_host,
        port=config.api_port,
        workers=config.workers,
        reload=config.debug,
    )
