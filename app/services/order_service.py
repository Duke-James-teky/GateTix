from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.user import User
from app.utils.pagination import PageParams, paginate


def list_my_orders(db: Session, buyer: User, params: PageParams) -> dict:
    """List the buyer's own orders, newest first."""
    query = select(Order).where(Order.attendee_id == buyer.id).order_by(Order.id.desc())
    return paginate(db, query, params)