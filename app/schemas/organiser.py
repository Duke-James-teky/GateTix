from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ApplicationStatus

class OrganiserApplicationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    organisation_name: str = Field(min_length=2, max_length=150)

class OrganiserApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field()
    user_id: int = Field()
    organisation_name: str = Field()
    status: ApplicationStatus = Field()
    reviewed_by: int | None = Field(default=None)

    