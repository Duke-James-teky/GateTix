from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.user import User
from app.utils.pagination import PageParams, paginate
from app.utils.ticket_codes import generate_ticket_code


def issue_tickets(db: Session, order: Order) -> list[Ticket]:
    """Create one ticket with its own unique code for every seat in a paid order.

    This does not commit. The caller commits, so the order, the tier counters and
    the tickets are saved together or not at all.
    """
    if order.status != OrderStatus.PAID:
        raise ConflictError("Tickets can only be issued for paid orders")

    already_issued = db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.order_id == order.id)
    )
    if already_issued:
        raise ConflictError("Tickets were already issued for this order")

    tickets = [
        Ticket(order_id=order.id, code=generate_ticket_code())
        for _ in range(order.quantity)
    ]
    db.add_all(tickets)
    db.flush()
    return tickets


def list_my_tickets(db: Session, buyer: User, params: PageParams) -> dict:
    """List the tickets that belong to the buyer's orders, newest first."""
    query = (
        select(Ticket)
        .join(Order, Ticket.order_id == Order.id)
        .where(Order.attendee_id == buyer.id)
        .order_by(Ticket.id.desc())
    )
    return paginate(db, query, params)