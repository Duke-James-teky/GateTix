from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.enums import ApplicationStatus, enum_column_type

