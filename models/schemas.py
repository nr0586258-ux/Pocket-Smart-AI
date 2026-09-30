"""Input / output schemas."""
from pydantic import BaseModel, Field, field_validator

MAX_BUDGET = 100_000_000


class HomeItem(BaseModel):
    room: str = Field(min_length=1, max_length=40)
    item: str = Field(min_length=1, max_length=60)
    quantity: int = Field(default=1, ge=1, le=50)


class HomeRequest(BaseModel):
    budget: float = Field(gt=0, le=MAX_BUDGET)
    style: str = Field(default="modern", max_length=60)
    notes: str = Field(default="", max_length=500)
    items: list[HomeItem] = Field(min_length=1, max_length=30)


class PartyRequest(BaseModel):
    budget: float = Field(gt=0, le=MAX_BUDGET)
    guests: int = Field(ge=1, le=5000)
    event_type: str = Field(min_length=1, max_length=40)
    venue: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=60)
    needs_stay: bool = False
    notes: str = Field(default="", max_length=500)


class JewelryRequest(BaseModel):
    budget: float = Field(gt=0, le=MAX_BUDGET)
    occasion: str = Field(min_length=1, max_length=60)
    style: str = Field(default="classic", max_length=60)
    metal: str = Field(default="any", max_length=40)
    notes: str = Field(default="", max_length=500)

    @field_validator("occasion", "style", "metal", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
