from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError
from app.models.event import Event
from app.models.ticket_tier import TicketTier
from app.schemas.ticket_tier import TierCreate, TierUpdate
from app.services.event_service import EDITABLE_STATUSES


def _ensure_event_editable(event: Event) -> None:
    if event.status not in EDITABLE_STATUSES:
        raise ConflictError(f"A {event.status} event cannot be changed")


def add_tier(db: Session, event: Event, data: TierCreate) -> TicketTier:
    """Add a ticket tier to a draft or published event."""
    _ensure_event_editable(event)

    duplicate = db.scalar(
        select(TicketTier.id).where(
            TicketTier.event_id == event.id, TicketTier.name == data.name
        )
    )
    if duplicate is not None:
        raise ConflictError(f"A tier named '{data.name}' already exists for this event")

    tier = TicketTier(event_id=event.id, **data.model_dump())
    db.add(tier)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f"A tier named '{data.name}' already exists for this event") from None
    return tier


def update_tier(db: Session, tier: TicketTier, data: TierUpdate) -> TicketTier:
    """Update a tier. Price and quantity are protected once tickets have sold."""
    event = db.get(Event, tier.event_id)
    _ensure_event_editable(event)

    # Lock the tier row and re-read it, so sold/reserved can't change while we validate.
    tier = db.scalar(
        select(TicketTier)
        .where(TicketTier.id == tier.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    updates = {
        field: value
        for field, value in data.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not updates:
        raise BadRequestError("No changes provided")

    if "price_kobo" in updates and updates["price_kobo"] != tier.price_kobo and tier.sold > 0:
        raise ConflictError("Price cannot change after tickets have been sold")

    quantity = updates.get("quantity", tier.quantity)
    committed = tier.sold + tier.reserved
    if quantity < committed:
        raise ConflictError(
            f"Quantity cannot be lower than the {committed} tickets already sold or held"
        )

    if updates.get("max_per_order", tier.max_per_order) > quantity:
        raise BadRequestError("max_per_order cannot be greater than quantity")

    sales_start = updates.get("sales_start", tier.sales_start)
    sales_end = updates.get("sales_end", tier.sales_end)
    if sales_end <= sales_start:
        raise BadRequestError("sales_end must be after sales_start")

    new_name = updates.get("name")
    if new_name is not None and new_name != tier.name:
        taken = db.scalar(
            select(TicketTier.id).where(
                TicketTier.event_id == tier.event_id,
                TicketTier.name == new_name,
                TicketTier.id != tier.id,
            )
        )
        if taken is not None:
            raise ConflictError(f"A tier named '{new_name}' already exists for this event")

    for field, value in updates.items():
        setattr(tier, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A tier with that name already exists for this event") from None
    return tier