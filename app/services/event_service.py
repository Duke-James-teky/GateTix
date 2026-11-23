from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.enums import EventStatus
from app.models.event import Event
from app.models.ticket_tier import TicketTier
from app.models.user import User
from app.schemas.event import EventCreate, EventUpdate
from app.services.reservation_service import release_expired_reservations
from app.utils.pagination import PageParams, paginate

EDITABLE_STATUSES = {EventStatus.DRAFT, EventStatus.PUBLISHED}


def create_event(db: Session, organiser: User, data: EventCreate) -> Event:
    """Create a draft event owned by the organiser."""
    event = Event(organiser_id=organiser.id, **data.model_dump())
    db.add(event)
    db.commit()
    return event


def update_event(db: Session, event: Event, data: EventUpdate) -> Event:
    """Apply the fields the organiser sent. Cancelled and suspended events are locked."""
    if event.status not in EDITABLE_STATUSES:
        raise ConflictError(f"A {event.status} event cannot be edited")

    updates = {
        field: value
        for field, value in data.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not updates:
        raise BadRequestError("No changes provided")

    # The schema can only compare dates sent together, so check against stored values too.
    starts_at = updates.get("starts_at", event.starts_at)
    ends_at = updates.get("ends_at", event.ends_at)
    if ends_at <= starts_at:
        raise BadRequestError("ends_at must be after starts_at")

    for field, value in updates.items():
        setattr(event, field, value)
    db.commit()
    return event


def publish_event(db: Session, event: Event) -> Event:
    """Make a draft event visible to attendees. It needs at least one ticket tier."""
    if event.status != EventStatus.DRAFT:
        raise ConflictError("Only draft events can be published")

    tier_count = db.scalar(
        select(func.count()).select_from(TicketTier).where(TicketTier.event_id == event.id)
    )
    if not tier_count:
        raise BadRequestError("Add at least one ticket tier before publishing")

    event.status = EventStatus.PUBLISHED
    db.commit()
    return event


def get_public_event(db: Session, event_id: int) -> Event:
    """Return a published event with its tiers. Anything else looks like it doesn't exist."""
    # Reservations whose time is up still count as "reserved" until someone releases
    # them, so release them first and the remaining-ticket counts are exact.
    release_expired_reservations(db, event_id)

    event = db.scalar(
        select(Event)
        .where(Event.id == event_id, Event.status == EventStatus.PUBLISHED)
        .options(selectinload(Event.tiers))
        .execution_options(populate_existing=True)
    )
    if event is None:
        raise NotFoundError("Event not found")
    return event


def list_events(
    db: Session,
    params: PageParams,
    city: str | None = None,
    category: str | None = None,
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
) -> dict:
    """List upcoming published events, soonest first, with optional filters."""
    if starts_after and starts_before and starts_after > starts_before:
        raise BadRequestError("starts_after must not be later than starts_before")

    query = select(Event).where(
        Event.status == EventStatus.PUBLISHED,
        Event.starts_at >= datetime.now(timezone.utc),
    )
    if city and city.strip():
        query = query.where(func.lower(Event.city) == city.strip().lower())
    if category and category.strip():
        query = query.where(func.lower(Event.category) == category.strip().lower())
    if starts_after:
        query = query.where(Event.starts_at >= starts_after)
    if starts_before:
        query = query.where(Event.starts_at <= starts_before)

    # The id breaks ties, so events with the same start time never swap pages.
    query = query.order_by(Event.starts_at, Event.id)
    return paginate(db, query, params)