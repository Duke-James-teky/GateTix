from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import EventStatus, OrderStatus
from app.models.event import Event
from app.models.order import Order
from app.schemas.admin import EventModeration, PlatformStats


def moderate_event(db: Session, event_id: int, decision: EventModeration) -> Event:
    """Suspend a published event, or restore a suspended one."""
    event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if event is None:
        raise NotFoundError("Event not found")

    target = EventStatus(decision.status)
    if target == EventStatus.SUSPENDED and event.status != EventStatus.PUBLISHED:
        raise ConflictError("Only published events can be suspended")
    if target == EventStatus.PUBLISHED and event.status != EventStatus.SUSPENDED:
        raise ConflictError("Only suspended events can be restored")

    event.status = target
    db.commit()
    return event


def get_platform_stats(db: Session) -> PlatformStats:
    """Totals for the admin dashboard. Tickets and revenue count paid orders only."""
    total_events = db.scalar(select(func.count(Event.id)))

    tickets_sold, revenue_kobo = db.execute(
        select(
            func.coalesce(func.sum(Order.quantity), 0),
            func.coalesce(func.sum(Order.total_kobo), 0),
        ).where(Order.status == OrderStatus.PAID)
    ).one()

    return PlatformStats(
        total_events=total_events,
        tickets_sold=int(tickets_sold),
        total_revenue_kobo=int(revenue_kobo),
    )