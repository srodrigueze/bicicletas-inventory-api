from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.bicycle import BicycleCondition, BicycleSize


class BicycleCreate(BaseModel):
    code: str = Field(..., max_length=5)
    condition: BicycleCondition = BicycleCondition.good
    size: BicycleSize = BicycleSize.medium
    rueditas_asistencia: bool
    tiene_pedales: bool
    observations: str | None = None


class BicycleUpdate(BaseModel):
    code: str | None = Field(default=None, max_length=5)
    condition: BicycleCondition | None = None
    size: BicycleSize | None = None
    rueditas_asistencia: bool | None = None
    tiene_pedales: bool | None = None
    observations: str | None = None


class BicycleRead(BaseModel):
    id: int
    code: str
    condition: BicycleCondition
    size: BicycleSize
    rueditas_asistencia: bool
    tiene_pedales: bool
    en_posesion_jac: bool
    observations: str | None
    is_available: bool

    model_config = ConfigDict(from_attributes=True)
