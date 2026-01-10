from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/subscription", tags=["subscription"])


class SubscriptionStatus(BaseModel):
    """Subscription status response."""
    plan: str
    credits_remaining: int
    credits_total: int
    is_low: bool
    is_active: bool
    expires_at: str | None = None


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionStatus:
    """Get current subscription status and credits."""
    # For now, return default values
    # TODO: Implement actual subscription tracking when billing is added

    # Check tenant for subscription info (future: use Stripe or similar)
    tenant = current_user.tenant

    # Default values - in future this would come from billing system
    credits_total = 1000
    credits_used = 0  # TODO: Track actual usage
    credits_remaining = credits_total - credits_used

    return SubscriptionStatus(
        plan="free",  # or "pro", "enterprise"
        credits_remaining=credits_remaining,
        credits_total=credits_total,
        is_low=credits_remaining < 100,
        is_active=True,
        expires_at=None,
    )
