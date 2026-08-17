"""FastAPI application for the ML Evaluation Platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import batch, discount, evaluation, health
from src.utils.config import get_config

STATIC_DIR = Path(__file__).parent / "static"


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
    docs_url="/api/docs",
    redoc_url="/api/redoc",
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
app.include_router(discount.router, prefix="/api/v1", tags=["discount"])


@app.get("/", include_in_schema=False)
async def landing_page():
    """Serve the product landing page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/docs", include_in_schema=False)
async def docs_index():
    """Serve the evaluator documentation index."""
    return FileResponse(STATIC_DIR / "docs" / "index.html")


@app.get("/docs/tier-1-rules", include_in_schema=False)
async def docs_tier1():
    """Serve Tier 1 rule-engine documentation."""
    return FileResponse(STATIC_DIR / "docs" / "tier-1-rules.html")


@app.get("/docs/tier-2-ml", include_in_schema=False)
async def docs_tier2():
    """Serve Tier 2 ML ensemble documentation."""
    return FileResponse(STATIC_DIR / "docs" / "tier-2-ml.html")


@app.get("/docs/tier-3-llm", include_in_schema=False)
async def docs_tier3():
    """Serve Tier 3 LLM-judge documentation."""
    return FileResponse(STATIC_DIR / "docs" / "tier-3-llm.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
