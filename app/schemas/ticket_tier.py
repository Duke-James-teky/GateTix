from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)


class TierCreate(BaseModel):
    """Data an organiser sends to add a ticket tier to an event."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, examples=["VIP"])
    price_kobo: int = Field(
        ge=0,
        description="Price in kobo (1 naira = 100 kobo). Use 0 for a free tier.",
        examples=[500000],
    )
    quantity: int = Field(ge=1, description="Total tickets in this tier.", examples=[100])
    sales_start: AwareDatetime = Field(examples=["2026-11-20T09:00:00Z"])
    sales_end: AwareDatetime = Field(examples=["2026-12-20T18:00:00Z"])
    max_per_order: int = Field(
        ge=1, description="Most tickets one order may contain.", examples=[4]
    )

    @model_validator(mode="after")
    def check_tier_rules(self):
        if self.sales_end <= self.sales_start:
            raise ValueError("sales_end must be after sales_start")
        if self.max_per_order > self.quantity:
            raise ValueError("max_per_order cannot be greater than quantity")
        return self


class TierUpdate(BaseModel):
    """Fields an organiser may change on a tier. Send only what you want to change."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100, examples=["VIP Plus"])
    price_kobo: int | None = Field(default=None, ge=0, examples=[600000])
    quantity: int | None = Field(default=None, ge=1, examples=[150])
    sales_start: AwareDatetime | None = Field(default=None, examples=["2026-11-22T09:00:00Z"])
    sales_end: AwareDatetime | None = Field(default=None, examples=["2026-12-22T18:00:00Z"])
    max_per_order: int | None = Field(default=None, ge=1, examples=[6])

    @model_validator(mode="after")
    def check_tier_rules(self):
        if self.sales_start and self.sales_end and self.sales_end <= self.sales_start:
            raise ValueError("sales_end must be after sales_start")
        if self.max_per_order and self.quantity and self.max_per_order > self.quantity:
            raise ValueError("max_per_order cannot be greater than quantity")
        return self


class TierRead(BaseModel):
    """A ticket tier as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[1])
    event_id: int = Field(examples=[3])
    name: str = Field(examples=["VIP"])
    price_kobo: int = Field(examples=[500000])
    quantity: int = Field(examples=[100])
    sold: int = Field(examples=[40])
    reserved: int = Field(description="Tickets currently held by unpaid reservations.", examples=[5])
    sales_start: AwareDatetime = Field(examples=["2026-11-20T09:00:00Z"])
    sales_end: AwareDatetime = Field(examples=["2026-12-20T18:00:00Z"])
    max_per_order: int = Field(examples=[4])

    @computed_field(description="Tickets still available: quantity - sold - reserved.", return_type=int)
    @property
    def remaining(self) -> int:
        return self.quantity - self.sold - self.reserved


class TierReport(BaseModel):
    """One row of the organiser's sales report."""

    tier_id: int = Field(examples=[1])
    name: str = Field(examples=["VIP"])
    sold: int = Field(examples=[40])
    remaining: int = Field(examples=[55])
    checked_in: int = Field(examples=[12])
    revenue_kobo: int = Field(examples=[20000000])