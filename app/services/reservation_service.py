from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.enums import EventStatus, OrderStatus
from app.models.event import Event
from app.models.order import Order
from app.models.ticket_tier import TicketTier
from app.models.user import User
from app.schemas.order import OrderCreate

settings = get_settings()


def _tickets(count: int) -> str:
    return f"{count} ticket" if count == 1 else f"{count} tickets"


def release_expired_reservations(db: Session, event_id: int) -> int:
    """Expire unpaid reservations whose time is up and give their tickets back to the tier."""
    now = datetime.now(timezone.utc)
    is_expired = (
        Order.event_id == event_id,
        Order.status == OrderStatus.PENDING,
        Order.expires_at <= now,
    )

    # Fast path: usually nothing has expired, so we lock nothing.
    if db.scalar(select(Order.id).where(*is_expired).limit(1)) is None:
        return 0

    # Lock every tier of the event in id order, so two cleanups can never deadlock.
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

    # Read the expired orders again now that we hold the locks.
    expired_orders = db.scalars(
        select(Order)
        .where(*is_expired)
        .order_by(Order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()

    for order in expired_orders:
        order.status = OrderStatus.EXPIRED
        tiers[order.tier_id].reserved -= order.quantity

    db.commit()
    return len(expired_orders)


def reserve_tickets(db: Session, attendee: User, data: OrderCreate) -> Order:
    """Hold tickets for the attendee for a limited time. Never sells more than exist."""
    tier = db.get(TicketTier, data.tier_id)
    if tier is None:
        raise NotFoundError("Ticket tier not found")

    event = db.get(Event, tier.event_id)
    if event is None or event.status != EventStatus.PUBLISHED:
        raise NotFoundError("Event not found")

    if event.starts_at <= datetime.now(timezone.utc):
        raise BadRequestError("This event has already started")

    #expired reservations are released before every new reservation.
    release_expired_reservations(db, event.id)

    already_pending = db.scalar(
        select(Order.id).where(
            Order.attendee_id == attendee.id,
            Order.event_id == event.id,
            Order.status == OrderStatus.PENDING,
        )
    )
    if already_pending is not None:
        raise ConflictError("You already have a pending reservation for this event")

    #lock the tier row. Anyone else reserving from this tier now waits.
    tier = db.scalar(
        select(TicketTier)
        .where(TicketTier.id == data.tier_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    now = datetime.now(timezone.utc)
    if now < tier.sales_start:
        raise BadRequestError("Ticket sales for this tier have not started yet")
    if now > tier.sales_end:
        raise BadRequestError("Ticket sales for this tier have ended")
    if data.quantity > tier.max_per_order:
        raise BadRequestError(
            f"You can buy at most {_tickets(tier.max_per_order)} per order"
        )

    available = tier.quantity - tier.sold - tier.reserved
    if available <= 0:
        raise ConflictError("Sold out")
    if data.quantity > available:
        raise ConflictError(f"Only {_tickets(available)} left")

    tier.reserved += data.quantity
    order = Order(
        attendee_id=attendee.id,
        tier_id=tier.id,
        event_id=event.id,
        quantity=data.quantity,
        total_kobo=tier.price_kobo * data.quantity,
        status=OrderStatus.PENDING,
        expires_at=now + timedelta(minutes=settings.reservation_hold_minutes),
    )
    db.add(order)
    try:
        db.commit()  # saves the order and the new counter together, then releases the lock
    except IntegrityError:
        db.rollback()
        raise ConflictError("You already have a pending reservation for this event") from None
    return order