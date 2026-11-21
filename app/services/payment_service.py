from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.enums import EventStatus, OrderStatus
from app.models.event import Event
from app.models.order import Order
from app.models.ticket_tier import TicketTier
from app.services.ticket_service import issue_tickets


def pay_order(db: Session, order: Order) -> Order:
    """Simulated payment: confirms a pending reservation and issues its tickets."""
    # Lock order: the tier first, then the order. Every service follows this order
    # so two requests can never wait on each other forever (a deadlock).
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

    if order.status == OrderStatus.PAID:
        raise ConflictError("This order has already been paid")
    if order.status == OrderStatus.REFUNDED:
        raise ConflictError("This order has been refunded")
    if order.status == OrderStatus.EXPIRED:
        raise ConflictError("This reservation has expired. Please reserve again")

    if order.expires_at <= datetime.now(timezone.utc):
        # Time ran out before payment arrived. Give the tickets back now and keep
        # that change, so the seats are free even though this request fails.
        order.status = OrderStatus.EXPIRED
        tier.reserved -= order.quantity
        db.commit()
        raise ConflictError("This reservation has expired. Please reserve again")

    event = db.get(Event, order.event_id)
    if event is None or event.status != EventStatus.PUBLISHED:
        raise ConflictError("This event is not currently on sale")

    # The held tickets become sold tickets. sold + reserved stays the same.
    order.status = OrderStatus.PAID
    tier.reserved -= order.quantity
    tier.sold += order.quantity
    db.flush()
    issue_tickets(db, order)
    db.commit()

    db.refresh(order, attribute_names=["tickets"])
    return order