from collections.abc import Callable
from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, Unau
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.enums import UserRole
from app.models.event import Event
from app.models.order import Order
from app.models.ticket_tier import TicketTier
from app.models.user import User