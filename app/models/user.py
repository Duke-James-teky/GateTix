from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import UserRole, enum_column_type


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        enum_column_type(UserRole, "user_role"),
        default=UserRole.ATTENDEE,
        server_default=UserRole.ATTENDEE.value,
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))