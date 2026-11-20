from fastapi import APIRouter

from app.core.dependencies import DbSession, OwnedTier
from app.routes.responses import (
    BAD_REQUEST,
    CONFLICT,
    FORBIDDEN,
    NOT_FOUND,
    UNAUTHORIZED,
)
from app.schemas.ticket_tier import TierRead, TierUpdate
from app.services import tier_service

router = APIRouter(prefix="/tiers", tags=["Ticket tiers"])


@router.patch(
    "/{tier_id}",
    response_model=TierRead,
    summary="Update a ticket tier",
    description=(
        "Owning organiser only. Once a tier has sold any ticket, its price cannot "
        "change and its quantity cannot drop below the tickets sold or held."
    ),
    responses={**BAD_REQUEST, **UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def update_tier(data: TierUpdate, tier: OwnedTier, db: DbSession):
    return tier_service.update_tier(db, tier, data)