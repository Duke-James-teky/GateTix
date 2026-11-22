from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import OrderStatus, TicketStatus
from app.models.event import Event
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.ticket_tier import TicketTier
from app.schemas.event import EventReport
from app.schemas.ticket_tier import TierReport
from app.services.reservation_service import release_expired_reservations


def get_event_report(db: Session, event: Event) -> EventReport:
    """Sold, remaining, checked-in and revenue for each tier of the event."""
    # Give back tickets from reservations that ran out of time, so "remaining" is exact.
    release_expired_reservations(db, event.id)

    tiers = db.scalars(
        select(TicketTier)
        .where(TicketTier.event_id == event.id)
        .order_by(TicketTier.id)
        .execution_options(populate_existing=True)
    ).all()

    revenue_rows = db.execute(
        select(Order.tier_id, func.coalesce(func.sum(Order.total_kobo), 0))
        .where(Order.event_id == event.id, Order.status == OrderStatus.PAID)
        .group_by(Order.tier_id)
    ).all()
    revenue = {tier_id: int(total) for tier_id, total in revenue_rows}

    checked_in_rows = db.execute(
        select(Order.tier_id, func.count(Ticket.id))
        .join(Ticket, Ticket.order_id == Order.id)
        .where(Order.event_id == event.id, Ticket.status == TicketStatus.USED)
        .group_by(Order.tier_id)
    ).all()
    checked_in = {tier_id: count for tier_id, count in checked_in_rows}

    rows = [
        TierReport(
            tier_id=tier.id,
            name=tier.name,
            sold=tier.sold,
            remaining=tier.quantity - tier.sold - tier.reserved,
            checked_in=checked_in.get(tier.id, 0),
            revenue_kobo=revenue.get(tier.id, 0),
        )
        for tier in tiers
    ]
    return EventReport(
        event_id=event.id,
        tiers=rows,
        total_sold=sum(row.sold for row in rows),
        total_checked_in=sum(row.checked_in for row in rows),
        total_revenue_kobo=sum(row.revenue_kobo for row in rows),
    )