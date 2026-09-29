from datetime import datetime

from sqlmodel import Session, select

from app.domain.entities.loan import Loan, LoanDetail, LoanDetailStatus
from app.domain.repositories.loan_repository import LoanRepository


class SqlLoanRepository(LoanRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, loan_id: int) -> Loan | None:
        return self.session.get(Loan, loan_id)

    def list_all(self, *, skip: int = 0, limit: int = 50) -> list[Loan]:
        statement = select(Loan).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def list_by_date_range(self, start_datetime: datetime, end_datetime: datetime) -> list[Loan]:
        statement = select(Loan).where(
            Loan.loan_datetime >= start_datetime,
            Loan.loan_datetime <= end_datetime,
        )
        return list(self.session.exec(statement).all())

    def list_active(self, *, skip: int = 0, limit: int = 50) -> list[Loan]:
        statement = (
            select(Loan)
            .join(LoanDetail, LoanDetail.loan_id == Loan.id)
            .where(LoanDetail.status == LoanDetailStatus.on_loan)
            .distinct()
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def get_active_loan_by_client_id(self, client_id: int) -> Loan | None:
        statement = (
            select(Loan)
            .join(LoanDetail, LoanDetail.loan_id == Loan.id)
            .where(Loan.client_id == client_id, LoanDetail.status == LoanDetailStatus.on_loan)
            .distinct()
        )
        return self.session.exec(statement).first()

    def create(self, loan: Loan) -> Loan:
        self.session.add(loan)
        self.session.commit()
        self.session.refresh(loan)
        return loan

    def list_details_by_loan(self, loan_id: int) -> list[LoanDetail]:
        statement = select(LoanDetail).where(LoanDetail.loan_id == loan_id)
        return list(self.session.exec(statement).all())

    def get_detail_by_id(self, detail_id: int) -> LoanDetail | None:
        return self.session.get(LoanDetail, detail_id)

    def add_detail(self, detail: LoanDetail) -> LoanDetail:
        self.session.add(detail)
        self.session.commit()
        self.session.refresh(detail)
        return detail

    def update_detail(self, detail: LoanDetail) -> LoanDetail:
        self.session.add(detail)
        self.session.commit()
        self.session.refresh(detail)
        return detail

    def get_active_detail_by_bicycle(self, bicycle_id: int) -> LoanDetail | None:
        statement = select(LoanDetail).where(
            LoanDetail.bicycle_id == bicycle_id,
            LoanDetail.status == LoanDetailStatus.on_loan,
        )
        return self.session.exec(statement).first()
