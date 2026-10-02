from enum import Enum

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class BicycleCondition(str, Enum):
    good = "good"
    bad = "bad"


class BicycleSize(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"


class Bicycle(SQLModel, table=True):
    # Defense-in-depth alongside the Field(ge=, le=) validation below: a CHECK
    # constraint rejects an out-of-range value even from a direct DB write
    # that bypasses the application layer entirely.
    __table_args__ = (sa.CheckConstraint("numero_frenos >= 0 AND numero_frenos <= 2", name="numero_frenos_range"),)

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(max_length=5, unique=True, index=True)
    condition: BicycleCondition = BicycleCondition.good
    size: BicycleSize = BicycleSize.medium
    rueditas_asistencia: bool
    tiene_pedales: bool
    en_posesion_jac: bool = True
    observations: str | None = None
    image_path: str | None = Field(default=None, max_length=255)
    numero_frenos: int = Field(default=2, ge=0, le=2)
