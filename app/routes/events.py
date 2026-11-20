from typing import Annotated

from fastapi import APIRouter, Query, status
from pydantic import AwareDatetime

from app.core.dependencies import DbSession, OrganiserUser, OwnedEvent
from app.routes.responses import (
    BAD_REQUEST,
    CONFLICT,
    FORBIDDEN,
    NOT_FOUND,
    UNAUTHORIZED,
)
from app.schemas.event import EventCreate, EventDetail, EventRead, EventUpdate
from app.schemas.pagination import Page
from app.schemas.ticket_tier import TierCreate, TierRead
from app.services import event_service, tier_service
from app.utils.pagination import PageQuery

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "",
    response_model=Page[EventRead],
    summary="Browse upcoming events",
    description=(
        "Open to everyone. Lists published events that have not started yet, soonest "
        "first, one page at a time. Filter by city, category and start-time range. "
        "City and category match the whole word, ignoring capital letters. "
        "Write times in UTC with a Z, for example `2027-01-01T00:00:00Z`."
    ),
    responses={**BAD_REQUEST},
)
def list_events(
    db: DbSession,
    page_params: PageQuery,
    city: Annotated[
        str | None, Query(description="Only events in this city", examples=["Lagos"])
    ] = None,
    category: Annotated[
        str | None, Query(description="Only events in this category", examples=["music"])
    ] = None,
    starts_after: Annotated[
        AwareDatetime | None,
        Query(description="Only events starting at or after this time", examples=["2027-01-01T00:00:00Z"]),
    ] = None,
    starts_before: Annotated[
        AwareDatetime | None,
        Query(description="Only events starting at or before this time", examples=["2027-12-31T23:59:59Z"]),
    ] = None,
):
    return event_service.list_events(
        db, page_params, city, category, starts_after, starts_before
    )


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft event",
    description="Organisers only. The event starts as a draft and is invisible to attendees until published.",
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def create_event(data: EventCreate, organiser: OrganiserUser, db: DbSession):
    return event_service.create_event(db, organiser, data)


@router.get(
    "/{event_id}",
    response_model=EventDetail,
    summary="Get one event with its ticket tiers",
    description=(
        "Open to everyone. Only published events are visible. Each tier shows how "
        "many tickets remain."
    ),
    responses={**NOT_FOUND},
)
def get_event(event_id: int, db: DbSession):
    return event_service.get_public_event(db, event_id)


@router.patch(
    "/{event_id}",
    response_model=EventRead,
    summary="Update an event",
    description="Owning organiser only. Send just the fields you want to change. Cancelled and suspended events cannot be edited.",
    responses={**BAD_REQUEST, **UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def update_event(data: EventUpdate, event: OwnedEvent, db: DbSession):
    return event_service.update_event(db, event, data)


@router.post(
    "/{event_id}/publish",
    response_model=EventRead,
    summary="Publish an event",
    description="Owning organiser only. The event must be a draft and have at least one ticket tier.",
    responses={**BAD_REQUEST, **UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def publish_event(event: OwnedEvent, db: DbSession):
    return event_service.publish_event(db, event)


@router.post(
    "/{event_id}/tiers",
    response_model=TierRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a ticket tier to an event",
    description="Owning organiser only. Prices are whole kobo (1 naira = 100 kobo). A price of 0 makes the tier free.",
    responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def add_tier(data: TierCreate, event: OwnedEvent, db: DbSession):
    return tier_service.add_tier(db, event, data)