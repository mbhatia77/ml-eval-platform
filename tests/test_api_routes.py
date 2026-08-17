"""Tests for health and evaluation API routes."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

# --- Fixtures ---


@pytest.fixture(scope="module")
def client():
    """HTTP client against the FastAPI app, with lifespan."""
    with TestClient(app) as test_client:
        yield test_client


def make_request_body(
    source: str = "The mitochondria is the powerhouse of the cell, responsible for producing ATP.",
    question: str = "What is the primary function of the mitochondria?",
    answer: str = "The primary function is to produce ATP through cellular respiration.",
) -> dict:
    """Build a valid EvaluationRequest body."""
    return {
        "source_document": source,
        "generated_question": question,
        "expected_answer": answer,
        "metadata": {
            "document_type": "general",
            "domain": "biology",
            "language": "en",
            "generation_model": "gpt-4",
            "prompt_version": "v1.0",
        },
    }


# --- Health ---


class TestHealthRoutes:
    """Test liveness and readiness probes."""

    def test_health_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["service"] == "ml-eval-platform"

    def test_readiness_ok(self, client: TestClient):
        response = client.get("/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["checks"]["kafka"] == "healthy"
        assert body["checks"]["redis"] == "healthy"
        assert body["checks"]["database"] == "healthy"
        assert body["checks"]["model_loaded"] is True


# --- POST /api/v1/evaluate ---


class TestEvaluateSubmit:
    """Test async evaluation submission."""

    def test_submit_accepted(self, client: TestClient):
        response = client.post("/api/v1/evaluate", json=make_request_body())
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        UUID(body["evaluation_id"])

    def test_empty_source_document(self, client: TestClient):
        response = client.post(
            "/api/v1/evaluate",
            json=make_request_body(source="   "),
        )
        assert response.status_code == 400
        assert "source_document" in response.json()["detail"]

    def test_empty_generated_question(self, client: TestClient):
        response = client.post(
            "/api/v1/evaluate",
            json=make_request_body(question="   "),
        )
        assert response.status_code == 400
        assert "generated_question" in response.json()["detail"]

    def test_missing_required_fields(self, client: TestClient):
        body = make_request_body()
        del body["expected_answer"]
        response = client.post("/api/v1/evaluate", json=body)
        assert response.status_code == 422

    def test_empty_expected_answer_still_accepted(self, client: TestClient):
        response = client.post(
            "/api/v1/evaluate",
            json=make_request_body(answer=""),
        )
        assert response.status_code == 202
        UUID(response.json()["evaluation_id"])


# --- GET /api/v1/evaluate/{id} ---


class TestEvaluateStatus:
    """Test evaluation status polling (placeholder)."""

    def test_status_pending_placeholder(self, client: TestClient):
        evaluation_id = "test-eval-123"
        response = client.get(f"/api/v1/evaluate/{evaluation_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["evaluation_id"] == evaluation_id
        assert body["status"] == "pending"
        assert body["result"] is None


# --- POST /api/v1/evaluate/sync ---


class TestEvaluateSync:
    """Test synchronous evaluation placeholder response."""

    def test_sync_returns_placeholder_result(self, client: TestClient):
        response = client.post("/api/v1/evaluate/sync", json=make_request_body())
        assert response.status_code == 200
        body = response.json()
        UUID(body["evaluation_id"])
        assert body["quality_score"] == 75.0
        assert body["confidence"] == 0.85
        assert body["decision"] == "pass"
        assert body["tier_used"] == 2


# --- Evaluator documentation pages ---


class TestDocsPages:
    """Test dedicated documentation pages for each evaluator."""

    @pytest.mark.parametrize(
        ("path", "heading"),
        [
            ("/docs", "Evaluator models"),
            ("/docs/tier-1-rules", "Tier 1 rule engine"),
            ("/docs/tier-2-ml", "Tier 2 ML ensemble"),
            ("/docs/tier-3-llm", "Tier 3 LLM judge"),
        ],
    )
    def test_docs_page_ok(self, client: TestClient, path: str, heading: str):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert heading in response.text

    def test_landing_links_to_docs(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert 'href="/docs"' in response.text
