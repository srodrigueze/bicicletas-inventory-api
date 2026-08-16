from enum import Enum

from sqlmodel import Field, SQLModel


class BicycleCondition(str, Enum):
    good = "good"
    bad = "bad"


class BicycleSize(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"


class Bicycle(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(max_length=5, unique=True, index=True)
    condition: BicycleCondition = BicycleCondition.good
    size: BicycleSize = BicycleSize.medium
    rueditas_asistencia: bool
    tiene_pedales: bool
    en_posesion_jac: bool = True
    observations: str | None = None
