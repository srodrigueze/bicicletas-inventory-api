from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.entities.bicycle import Bicycle


class LoanStatus(str, Enum):
    in_progress = "in_progress"
    finished = "finished"


class LoanBicycleLink(SQLModel, table=True):
    __tablename__ = "loan_bicycle_link"

    loan_id: int | None = Field(default=None, foreign_key="loan.id", primary_key=True)
    bicycle_id: int | None = Field(default=None, foreign_key="bicycle.id", primary_key=True)


class Loan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    requester_name: str = Field(max_length=50)
    id_document: str = Field(max_length=20)
    phone: str = Field(max_length=15)
    loan_datetime: datetime
    return_datetime: datetime | None = None
    status: LoanStatus = LoanStatus.in_progress

    bicycles: list["Bicycle"] = Relationship(link_model=LoanBicycleLink)
