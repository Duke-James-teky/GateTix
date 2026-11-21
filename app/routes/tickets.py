from fastapi import APIRouter

from app.core.dependencies import BuyerUser, DbSession
from app.routes.responses import FORBIDDEN, UNAUTHORIZED
from app.schemas.pagination import Page
from app.schemas.ticket import TicketRead
from app.services import ticket_service
from app.utils.pagination import PageQuery

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get(
    "",
    response_model=Page[TicketRead],
    summary="List my tickets",
    description="Your own tickets with their codes, newest first, one page at a time.",
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def list_tickets(buyer: BuyerUser, db: DbSession, page_params: PageQuery):
    return ticket_service.list_my_tickets(db, buyer, page_params)