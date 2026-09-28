from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.loan import LoanDetailStatus
from app.schemas.client import ClientData, ClientRead


class LoanCreate(BaseModel):
    bicycle_ids: list[int] = Field(..., min_length=1)
    client: ClientData


class LoanAddBicycles(BaseModel):
    bicycle_ids: list[int] = Field(..., min_length=1)


class LoanDetailRead(BaseModel):
    id: int
    bicycle_id: int
    status: LoanDetailStatus
    returned_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class LoanRead(BaseModel):
    id: int
    client: ClientRead
    loan_datetime: datetime
    is_active: bool
    details: list[LoanDetailRead]

    model_config = ConfigDict(from_attributes=True)
