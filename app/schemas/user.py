from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.enums import UserRole

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(default=1)
    name: str = Field("Duke")
    email: str = Field(default="dukybiz@gmail.com")
    role: UserRole = Field(default="attendee")
    is_active: bool = Field(default=True)

    