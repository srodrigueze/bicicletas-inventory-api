from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class LoanDetailStatus(str, Enum):
    on_loan = "on_loan"
    returned = "returned"


class Loan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    loan_datetime: datetime


class LoanDetail(SQLModel, table=True):
    __tablename__ = "loan_detail"

    id: int | None = Field(default=None, primary_key=True)
    loan_id: int = Field(foreign_key="loan.id")
    bicycle_id: int = Field(foreign_key="bicycle.id")
    status: LoanDetailStatus = LoanDetailStatus.on_loan
    returned_at: datetime | None = None
