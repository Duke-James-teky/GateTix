from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from app.schemas.ticket_tier import TierReport, TierRead

class EventCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    venue: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    start_at: AwareDatetime = Field()
    ends_at: AwareDatetime = Field()
    