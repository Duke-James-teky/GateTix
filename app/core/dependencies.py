from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.enums import UserRole
from app.models.event import Event
from app.models.order import Order
from app.models.ticket_tier import TicketTier
from app.models.user import User

# auto_error=False lets us raise our own consistent 401 JSON error.
bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


#who is calling

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    """Read the token, load the user from the database, and reject bad or inactive users."""
    if credentials is None:
        raise UnauthorizedError("Not authenticated")

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise UnauthorizedError("Invalid or expired token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


#Role check

def require_roles(*allowed_roles: UserRole) -> Callable[..., User]:
    """Build a dependency that only lets users with one of the given roles through."""

    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError("You do not have permission to do this")
        return current_user

    return role_checker


require_attendee = require_roles(UserRole.ATTENDEE)
require_buyer = require_roles(UserRole.ATTENDEE, UserRole.ORGANISER)
require_organiser = require_roles(UserRole.ORGANISER)
require_admin = require_roles(UserRole.ADMIN)

AttendeeUser = Annotated[User, Depends(require_attendee)]
BuyerUser = Annotated[User, Depends(require_buyer)]
OrganiserUser = Annotated[User, Depends(require_organiser)]
AdminUser = Annotated[User, Depends(require_admin)]


#ownership check

def get_owned_event(event_id: int, organiser: OrganiserUser, db: DbSession) -> Event:
    """Load an event and make sure the calling organiser owns it."""
    event = db.get(Event, event_id)
    if event is None:
        raise NotFoundError("Event not found")
    if event.organiser_id != organiser.id:
        raise ForbiddenError("You can only manage your own events")
    return event


def get_owned_tier(tier_id: int, organiser: OrganiserUser, db: DbSession) -> TicketTier:
    """Load a ticket tier and make sure the calling organiser owns its event."""
    tier = db.get(TicketTier, tier_id)
    if tier is None:
        raise NotFoundError("Ticket tier not found")
    event = db.get(Event, tier.event_id)
    if event is None or event.organiser_id != organiser.id:
        raise ForbiddenError("You can only manage tiers of your own events")
    return tier


def get_own_order(order_id: int, buyer: BuyerUser, db: DbSession) -> Order:
    """Load an order and make sure it belongs to the calling user."""
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("Order not found")
    if order.attendee_id != buyer.id:
        raise ForbiddenError("You can only access your own orders")
    return order


OwnedEvent = Annotated[Event, Depends(get_owned_event)]
OwnedTier = Annotated[TicketTier, Depends(get_owned_tier)]
OwnOrder = Annotated[Order, Depends(get_own_order)]