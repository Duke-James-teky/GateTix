from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.enums import ApplicationStatus, enum_column_type

class OrganiserApplication(Base):
    __tablename__ = "organiser_applications"
    __table_args__ = (
        Index(
            "one_pending_application_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    organisation_name: Mapped[str] = mapped_column(String(150))
    status: Mapped[ApplicationStatus] = mapped_column(
        enum_column_type(ApplicationStatus, "application_status"),
        default=ApplicationStatus.PENDING,
        server_default=ApplicationStatus.PENDING.value,
        index=True
    )
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    