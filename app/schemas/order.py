from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app.models.enums import OrderStatus
from app.schemas.ticket import TicketRead

class OrderCreate(BaseModel):
    tier_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field()
    attendee_id: int = Field()
    tier_id: int = Field()
    quantity: int = Field()
    total_kobo: int = Field()
    status: OrderStatus = Field()
    expires_at: datetime | None = Field(default= None)
    created_at: datetime = Field()

class OrderWithTickets(OrderRead):
    tickets: list[TicketRead] = Field(default_factory= list)
    