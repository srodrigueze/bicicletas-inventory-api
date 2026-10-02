from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.bicycle import BicycleCondition, BicycleSize


class BicycleCreate(BaseModel):
    code: str = Field(..., max_length=5)
    condition: BicycleCondition = BicycleCondition.good
    size: BicycleSize = BicycleSize.medium
    rueditas_asistencia: bool
    tiene_pedales: bool
    observations: str | None = None
    image_path: str | None = Field(default=None, max_length=255)
    numero_frenos: int = Field(default=2, ge=0, le=2)


class BicycleUpdate(BaseModel):
    code: str | None = Field(default=None, max_length=5)
    condition: BicycleCondition | None = None
    size: BicycleSize | None = None
    rueditas_asistencia: bool | None = None
    tiene_pedales: bool | None = None
    observations: str | None = None
    image_path: str | None = Field(default=None, max_length=255)
    numero_frenos: int | None = Field(default=None, ge=0, le=2)


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
    image_path: str | None
    image_url: str | None
    numero_frenos: int

    model_config = ConfigDict(from_attributes=True)
