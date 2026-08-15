from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.bicycle import BicycleCondition, BicycleSize


class BicycleCreate(BaseModel):
    code: str = Field(..., max_length=5)
    condition: BicycleCondition = BicycleCondition.good
    size: BicycleSize = BicycleSize.medium
    observations: str | None = None


class BicycleUpdate(BaseModel):
    code: str | None = Field(default=None, max_length=5)
    condition: BicycleCondition | None = None
    size: BicycleSize | None = None
    observations: str | None = None
    photo_url: str | None = None


class BicycleRead(BaseModel):
    id: int
    code: str
    condition: BicycleCondition
    size: BicycleSize
    observations: str | None
    photo_url: str | None
    is_available: bool  # derived: good condition AND no active loan on this bicycle

    model_config = ConfigDict(from_attributes=True)
