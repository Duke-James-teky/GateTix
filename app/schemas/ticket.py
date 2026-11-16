from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app.models.enums import TicketStatus

class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field()
    order_id: int = Field()
    code: str = Field()
    status: TicketStatus = Field()
    checked_in_at: datetime | None = Field(default=None)

class CheckedInRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(min_length=8, max_length=60)

