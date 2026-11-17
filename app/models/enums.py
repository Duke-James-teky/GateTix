from enum import StrEnum
from sqlalchemy import Enum as SAEnum

class UserRole(StrEnum):
    ATTENDEE = "attendee"
    ORGANISER = "organiser"
    ADMIN = "admin"

class ApplicationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"

class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    REFUNDED = "refunded"

class TicketStatus(StrEnum):
    VALID = "valid"
    USED = "used"
    REFUNDED = "refunded"

def enum_column_type(enum_class: type[StrEnum], name: str) -> SAEnum:
    """column type that stores an enum as a short text valued"""
    return SAEnum(
        enum_class,
        name=name,
        native_enum=False,
        length=20,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
    )
