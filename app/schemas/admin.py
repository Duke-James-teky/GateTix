from pydantic import BaseModel, Field
from typing import Literal
from app.models.enums import ApplicationStatus, EventStatus

class OrganiserDecision(BaseModel):
    status: Literal[ApplicationStatus.APPROVED, ApplicationStatus.REJECTED] = Field(description="Approve or reject the application")

class EventModeration(BaseModel):
    status: Literal[EventStatus.SUSPENDED, EventStatus.PUBLISHED] = Field()

class PlatformStats(BaseModel):
    