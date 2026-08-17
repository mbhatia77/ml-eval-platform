"""Tests for the landing page and discount apply API."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import discount as discount_routes


@pytest.fixture
def client():
    """HTTP client against the FastAPI app, with lifespan."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_redemptions():
    """Keep the in-memory store isolated across tests."""
    discount_routes._redemptions.clear()
    yield
    discount_routes._redemptions.clear()


class TestLandingPage:
    """Test the static landing page served at GET /."""

    def test_landing_returns_html(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        body = response.text.lower()
        assert "discount" in body
        assert "ml evaluation platform" in body

    def test_static_stylesheet_served(self, client: TestClient):
        response = client.get("/static/styles.css")
        assert response.status_code == 200


class TestApplyDiscount:
    """Test POST /api/v1/discount/apply."""

    def test_valid_code_applied(self, client: TestClient):
        response = client.post(
            "/api/v1/discount/apply",
            json={"code": "LAUNCH20"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["applied"] is True
        assert body["code"] == "LAUNCH20"
        assert body["percent_off"] == 20
        UUID(body["redemption_id"])

    def test_code_is_normalized(self, client: TestClient):
        response = client.post(
            "/api/v1/discount/apply",
            json={"code": "  eval50  "},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == "EVAL50"
        assert body["percent_off"] == 50

    def test_unknown_code_rejected(self, client: TestClient):
        response = client.post(
            "/api/v1/discount/apply",
            json={"code": "NOTREAL"},
        )
        assert response.status_code == 400
        assert "Invalid discount code" in response.json()["detail"]

    def test_blank_code_rejected(self, client: TestClient):
        response = client.post(
            "/api/v1/discount/apply",
            json={"code": "   "},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_email_is_recorded_on_redemption(self, client: TestClient):
        response = client.post(
            "/api/v1/discount/apply",
            json={"code": "LAUNCH20", "email": "user@example.com"},
        )
        assert response.status_code == 200
        assert len(discount_routes._redemptions) == 1
        redemption = discount_routes._redemptions[0]
        assert redemption["email"] == "user@example.com"
        assert redemption["code"] == "LAUNCH20"
        assert redemption["redemption_id"] == response.json()["redemption_id"]
