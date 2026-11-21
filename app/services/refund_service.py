from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError
from app.models.enums import EventStatus, OrderStatus, TicketStatus
from app.models.event import Event
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.ticket_tier import TicketTier

REFUND_CUTOFF = timedelta(hours=48)
CANCELLABLE_STATUSES = {EventStatus.DRAFT, EventStatus.PUBLISHED}


def _refund_paid_order(db: Session, order: Order, tier: TicketTier) -> None:
    """Mark a paid order refunded, void its tickets and return the seats to the tier.

    The caller holds the locks and commits.
    """
    order.status = OrderStatus.REFUNDED
    tier.sold -= order.quantity
    db.execute(
        update(Ticket)
        .where(Ticket.order_id == order.id, Ticket.status == TicketStatus.VALID)
        .values(status=TicketStatus.REFUNDED)
    )


def refund_order(db: Session, order: Order) -> Order:
    """Refund a paid order, up to 48 hours before the event starts."""
    # Lock order: the tier first, then the order, as in every other service.
    tier = db.scalar(
        select(TicketTier)
        .where(TicketTier.id == order.tier_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = db.scalar(
        select(Order)
        .where(Order.id == order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if order.status == OrderStatus.REFUNDED:
        raise ConflictError("This order has already been refunded")
    if order.status != OrderStatus.PAID:
        raise ConflictError("Only paid orders can be refunded")

    event = db.get(Event, order.event_id)
    if event.starts_at - datetime.now(timezone.utc) < REFUND_CUTOFF:
        raise BadRequestError("Refunds close 48 hours before the event starts")

    used = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.order_id == order.id, Ticket.status == TicketStatus.USED)
    )
    if used:
        raise ConflictError("Tickets from this order have already been used")

    _refund_paid_order(db, order, tier)
    db.commit()
    return order


def cancel_event(db: Session, event: Event) -> Event:
    """Cancel an event. Paid orders are refunded and unpaid reservations are released."""
    event_id = event.id

    # Lock every tier of the event in id order, then the event itself, then its orders.
    tiers = {
        tier.id: tier
        for tier in db.scalars(
            select(TicketTier)
            .where(TicketTier.event_id == event_id)
            .order_by(TicketTier.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    }
    event = db.scalar(
        select(Event)
        .where(Event.id == event_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if event.status == EventStatus.CANCELLED:
        raise ConflictError("This event is already cancelled")
    if event.status not in CANCELLABLE_STATUSES:
        raise ConflictError(f"A {event.status} event cannot be cancelled")

    orders = db.scalars(
        select(Order)
        .where(
            Order.event_id == event_id,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.PAID]),
        )
        .order_by(Order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()

    for order in orders:
        tier = tiers[order.tier_id]
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.EXPIRED
            tier.reserved -= order.quantity
        else:
            _refund_paid_order(db, order, tier)

    event.status = EventStatus.CANCELLED
    db.commit()
    return event