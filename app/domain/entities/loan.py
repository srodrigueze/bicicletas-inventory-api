from datetime import datetime
from enum import Enum

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class LoanDetailStatus(str, Enum):
    on_loan = "on_loan"
    returned = "returned"
    incumplido = "incumplido"


class Loan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    loan_datetime: datetime


class LoanDetail(SQLModel, table=True):
    __tablename__ = "loan_detail"
    # Defense-in-depth against the race window between the app-level
    # availability check (SELECT) and this row's INSERT: two near-simultaneous
    # requests could both pass the check for the same bicycle before either
    # commits. This partial unique index makes the second INSERT fail at the
    # database level regardless of timing, closing the window the app-level
    # check alone can't (see DEV-003, RN-REQ003-19).
    __table_args__ = (
        sa.Index(
            "one_active_loan_per_bicycle",
            "bicycle_id",
            unique=True,
            postgresql_where=sa.text("status = 'on_loan'"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    loan_id: int = Field(foreign_key="loan.id")
    bicycle_id: int = Field(foreign_key="bicycle.id")
    status: LoanDetailStatus = LoanDetailStatus.on_loan
    returned_at: datetime | None = None
