from enum import StrEnum

class UserRole(StrEnum):
    ATTENDEE = "attendee"
    ORGANISER = "organiser"
    ADMIN = "admin"

class ApplicationStatus(StrEnum):
    