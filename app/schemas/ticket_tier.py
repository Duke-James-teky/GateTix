from pydantic import AwareDatetime, BaseModel,ConfigDict, Field, model_validator, computed_field

class TierCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    price_kobo: int = Field(ge=0)
    quantity: int = Field(ge=1)
    sales_end: AwareDatetime = Field()
    max_per_order: int = Field(ge=1)

@model_validator(mode="after")
def check_tier_rules(self):
    if self.sales_end <= self.sales_start:
        raise ValueError("sales end must be after sales start")
    if self.max_per_order > self.quantity:
        raise ValueError("max per order cannot be greater than quantity")
    return self

class TierUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default= None, min_length=1, max_length=100)
    price_kobo: int | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, ge=1)
    sales_start: AwareDatetime | None = Field(default=None)
    sales_end: AwareDatetime | None = Field(default=None)
    max_per_order: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def check_tier_rules(self):
        if self.sales_start and self.sales_end and self.sales_end <= self.sales_start:
            raise ValueError("sales end must be after sales start")
        if self.max_per_order and self.quantity and self.max_per_order > self.quantity:
            raise ValueError("max per order cannot be more than quantity")
        return self

class TierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field()
    event_id: int = Field()
    name: str = Field()
    price_kobo: int = Field()
    quantity: int = Field()
    sold: int = Field()
    reserved: int = Field(description= "Tickets currently held by unpaid reservations")
    sales_start: AwareDatetime = Field()
    sales_end: AwareDatetime = Field()
    max_per_order: int = Field()

    @computed_field(description="ticket still available, quantity, solde, reserved", return_type=int)
    @property
    def remaining(self) -> int:
        return self.quantity - self.sold - self.reserved
    
class TierReport(BaseModel):
    tier_id: int = Field()
    name: str = Field(examples=["VIP"])
    sold: int = Field()
    remaining: int = Field()
    checked_in: int = Field()
    revenue_kobo: int = Field()