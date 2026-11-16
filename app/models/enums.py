from enum import StrEnum

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

class OrderStatus(StrEnum)
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    REFUNDED = "refunded"

class TicketStatus(StrEnum):
    VALID = "valid"
    USED = "used"
    REFUNDED = "refunded"
    