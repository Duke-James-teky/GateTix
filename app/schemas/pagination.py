from pydantic import BaseModel, Field, computed_field
from typing import Generic, TypeVar
import math

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: list[T] = Field(description="the results on the page")
    total: int = Field(ge=0,description="total results across all pages")
    page: int = Field(ge=1, description="current page number, starting form 1")
    size: int = Field(ge=1, description="maximum results per page")
    