from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.loan import LoanStatus


class LoanCreate(BaseModel):
    bicycle_ids: list[int] = Field(..., min_length=1)
    requester_name: str = Field(..., max_length=50)
    id_document: str = Field(..., max_length=20)
    phone: str = Field(..., max_length=15)
    loan_datetime: datetime


class LoanReturn(BaseModel):
    return_datetime: datetime | None = None


class LoanRead(BaseModel):
    id: int
    requester_name: str
    id_document: str
    phone: str
    loan_datetime: datetime
    return_datetime: datetime | None
    status: LoanStatus
    bicycle_ids: list[int]

    model_config = ConfigDict(from_attributes=True)
