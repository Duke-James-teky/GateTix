from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from app.schemas.ticket_tier import TierReport, TierRead
from app.models.enums import EventStatus

class EventCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    venue: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    start_at: AwareDatetime = Field()
    ends_at: AwareDatetime = Field()

    @model_validator(mode="after")
    def check_times(self):
        if self.ends_at <= self.start_at:
            raise ValueError("please put in a valid ends at ")
        return self

class EventUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    venue: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    starts_at: AwareDatetime | None = Field(default=None)
    ends_at: AwareDatetime | None = Field(default=None)

    @model_validator(mode="after")
    def check_times(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends at must be after starts_at")
        return self

class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field()
    organiser_id: int = Field()
    title: str = Field()
    description: str = Field()
    venue: str = Field()
    city: str = Field()
    category: str = Field()
    starts_at: AwareDatetime = Field()
    ends_at: AwareDatetime = Field()
    status: EventStatus = Field()

class EventDetail(EventRead):
    tiers: list[TierRead] = Field(default_factory=list)

class EventReport(BaseModel):
    event_id: int = Field()
    tiers: list[TierRead]
    total_sold: int = Field()
    total_checked_in: int = Field()
    total_revenue_kobo: int = Field()
    