from fastapi import APIRouter

from app.core.dependencies import DbSession, OwnedEvent
from app.routes.responses import (
    BAD_REQUEST,
    CONFLICT,
    FORBIDDEN,
    NOT_FOUND,
    UNAUTHORIZED,
)
from app.schemas.ticket import CheckInRequest, CheckInResponse
from app.services import checkin_service

router = APIRouter(prefix="/events", tags=["Check-in"])


@router.post(
    "/{event_id}/check-in",
    response_model=CheckInResponse,
    summary="Check in a ticket by its code",
    description=(
        "Owning organiser only, and only on the day of the event. A valid ticket is "
        "marked used. Scanning the same code a second time is rejected, even if two "
        "scans arrive at the same instant. Refunded tickets never check in."
    ),
    responses={**BAD_REQUEST, **UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def check_in(data: CheckInRequest, event: OwnedEvent, db: DbSession):
    ticket = checkin_service.check_in_ticket(db, event, data.code)
    return {"message": "Ticket checked in", "ticket": ticket}