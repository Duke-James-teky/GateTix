from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass
class PageParams:
    """Which slice of a list the client asked for."""

    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def get_page_params(
    page: Annotated[int, Query(ge=1, description="Page number, starting at 1")] = 1,
    size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description=f"Results per page (maximum {MAX_PAGE_SIZE})"),
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, size=size)


PageQuery = Annotated[PageParams, Depends(get_page_params)]


def paginate(db: Session, query: Select, params: PageParams) -> dict:
    """Run a query one page at a time and return the data a Page schema expects."""
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = db.scalars(query.limit(params.size).offset(params.offset)).all()
    return {"items": items, "total": total, "page": params.page, "size": params.size}