from datetime import datetime

from sqlalchemy.exc import IntegrityError
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

    def _has_detail_status(self, status: LoanDetailStatus):
        return (
            select(LoanDetail.id)
            .where(LoanDetail.loan_id == Loan.id, LoanDetail.status == status)
            .exists()
        )

    def list_filtered(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
    ) -> list[Loan]:
        statement = select(Loan)
        if start_datetime is not None:
            statement = statement.where(Loan.loan_datetime >= start_datetime)
        if end_datetime is not None:
            statement = statement.where(Loan.loan_datetime <= end_datetime)

        if status == "activo":
            statement = statement.where(self._has_detail_status(LoanDetailStatus.on_loan))
        elif status == "incumplido":
            statement = statement.where(
                ~self._has_detail_status(LoanDetailStatus.on_loan),
                self._has_detail_status(LoanDetailStatus.incumplido),
            )
        elif status == "cerrado":
            statement = statement.where(
                ~self._has_detail_status(LoanDetailStatus.on_loan),
                ~self._has_detail_status(LoanDetailStatus.incumplido),
            )

        statement = statement.order_by(Loan.loan_datetime.desc()).offset(skip).limit(limit)
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
        try:
            self.session.commit()
        except IntegrityError:
            # Two near-simultaneous requests can both pass the app-level
            # availability check before either commits; the partial unique
            # index (one_active_loan_per_bicycle) is what actually stops the
            # second one. Roll back so the session is usable again and let
            # the caller translate this into a business conflict.
            self.session.rollback()
            raise
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
