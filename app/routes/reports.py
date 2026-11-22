from fastapi import APIRouter

from app.core.dependencies import DbSession, OwnedEvent
from app.routes.responses import FORBIDDEN, NOT_FOUND, UNAUTHORIZED
from app.schemas.event import EventReport
from app.services import report_service

router = APIRouter(prefix="/events", tags=["Reports"])


@router.get(
    "/{event_id}/report",
    response_model=EventReport,
    summary="Sales report for an event",
    description=(
        "Owning organiser only. For each ticket tier: tickets sold, tickets still "
        "available, tickets checked in at the gate, and revenue in kobo. "
        "Refunded orders are not counted."
    ),
    responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND},
)
def event_report(event: OwnedEvent, db: DbSession):
    return report_service.get_event_report(db, event)