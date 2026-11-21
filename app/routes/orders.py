from fastapi import APIRouter, status

from app.core.dependencies import BuyerUser, DbSession, OwnOrder
from app.routes.responses import (
    BAD_REQUEST,
    CONFLICT,
    FORBIDDEN,
    NOT_FOUND,
    UNAUTHORIZED,
)
from app.schemas.order import OrderCreate, OrderRead, OrderWithTickets
from app.schemas.pagination import Page
from app.services import order_service, payment_service, reservation_service
from app.utils.pagination import PageQuery

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderWithTickets,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve tickets",
    description=(
        "Attendees and organisers. Holds the tickets for 10 minutes while you pay. "
        "You can hold only one pending reservation per event. "
        "A free tier (price 0) skips payment: the order comes back already paid, "
        "with its tickets."
    ),
    responses={**BAD_REQUEST, **UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def reserve(data: OrderCreate, buyer: BuyerUser, db: DbSession):
    return reservation_service.reserve_tickets(db, buyer, data)


@router.get(
    "",
    response_model=Page[OrderRead],
    summary="List my orders",
    description="Your own orders only, newest first, one page at a time.",
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def list_orders(buyer: BuyerUser, db: DbSession, page_params: PageQuery):
    return order_service.list_my_orders(db, buyer, page_params)


@router.post(
    "/{order_id}/pay",
    response_model=OrderWithTickets,
    summary="Pay for a reservation (simulated)",
    description=(
        "Order's owner only. Pretends the payment succeeded, turns the reservation "
        "into a paid order, and issues one ticket with a unique code per seat. "
        "If the 10 minutes have passed, the reservation expires and the payment is refused."
    ),
    responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def pay(order: OwnOrder, db: DbSession):
    return payment_service.pay_order(db, order)