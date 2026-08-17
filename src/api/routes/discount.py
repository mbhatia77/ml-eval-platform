"""Discount code application endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.utils.config import get_config

router = APIRouter()

# In-memory redemption log. In production: INSERT into PostgreSQL.
_redemptions: list[dict] = []


class DiscountApplyRequest(BaseModel):
    """Request body for applying a landing-page discount code."""

    code: str
    email: str | None = None


class DiscountApplyResponse(BaseModel):
    """Successful discount application."""

    applied: bool = True
    code: str
    percent_off: int = Field(ge=0, le=100)
    redemption_id: str


def _normalize_code(code: str) -> str:
    return code.strip().upper()


@router.post(
    "/discount/apply",
    response_model=DiscountApplyResponse,
)
async def apply_discount(request: DiscountApplyRequest):
    """
    Validate a discount code against the configured allowlist and record it.

    Used by the landing page before a future signup flow.
    """
    code = _normalize_code(request.code)
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount code cannot be empty",
        )

    allowlist = {
        name.upper(): percent for name, percent in get_config().discount.codes.items()
    }
    percent_off = allowlist.get(code)
    if percent_off is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid discount code",
        )

    redemption_id = str(uuid.uuid4())
    _redemptions.append(
        {
            "redemption_id": redemption_id,
            "code": code,
            "email": request.email,
            "percent_off": percent_off,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    # In production: persist the redemption to PostgreSQL

    return DiscountApplyResponse(
        applied=True,
        code=code,
        percent_off=percent_off,
        redemption_id=redemption_id,
    )
