from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """The JSON body of every error the API returns on purpose."""

    detail: str = Field(examples=["Event not found"])


class HealthResponse(BaseModel):
    """Result of the health check."""

    status: str = Field(examples=["ok"])
    database: str = Field(examples=["ok"])