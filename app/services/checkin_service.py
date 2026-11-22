from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.enums import EventStatus, TicketStatus
from app.models.event import Event
from app.models.order import Order
from app.models.ticket import Ticket

# "The day of the event" is a calendar day in Nigerian time (UTC+1, no daylight saving).
EVENT_TZ = timezone(timedelta(hours=1))


def _checkin_window(event: Event) -> tuple[datetime, datetime]:
    """Check-in opens at midnight of the event's day and closes at the end of that
    day, or at the event's end time if that is later."""
    day_start = event.starts_at.astimezone(EVENT_TZ).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return day_start, max(day_start + timedelta(days=1), event.ends_at)


def check_in_ticket(db: Session, event: Event, code: str) -> Ticket:
    """Mark a valid ticket of this event as used. A second scan is always rejected."""
    if event.status != EventStatus.PUBLISHED:
        raise ConflictError("Check-in is only open for published events")

    now = datetime.now(timezone.utc)
    opens_at, closes_at = _checkin_window(event)
    if not opens_at <= now <= closes_at:
        raise BadRequestError("Check-in is only open on the day of the event")

    # Challenge 3: one statement checks and changes the ticket together. Only a ticket
    # that is still 'valid' can match, so two scanners can never both succeed.
    ticket_id = db.scalar(
        update(Ticket)
        .where(
            Ticket.code == code,
            Ticket.status == TicketStatus.VALID,
            Ticket.order_id.in_(select(Order.id).where(Order.event_id == event.id)),
        )
        .values(status=TicketStatus.USED, checked_in_at=now)
        .returning(Ticket.id)
        .execution_options(synchronize_session=False)
    )

    if ticket_id is None:
        # Nothing was changed. Work out why, so the gate staff get a clear answer.
        existing = db.scalar(
            select(Ticket)
            .join(Order, Ticket.order_id == Order.id)
            .where(Ticket.code == code, Order.event_id == event.id)
        )
        if existing is None:
            raise NotFoundError("Ticket not found for this event")
        if existing.status == TicketStatus.USED:
            raise ConflictError("This ticket has already been used")
        raise ConflictError("This ticket is no longer valid")

    db.commit()
    return db.get(Ticket, ticket_id)