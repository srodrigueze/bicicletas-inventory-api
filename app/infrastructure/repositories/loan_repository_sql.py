from sqlmodel import Session, select

from app.domain.entities.loan import Loan, LoanBicycleLink, LoanStatus
from app.domain.repositories.loan_repository import LoanRepository


class SqlLoanRepository(LoanRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, loan_id: int) -> Loan | None:
        return self.session.get(Loan, loan_id)

    def list_all(self) -> list[Loan]:
        return list(self.session.exec(select(Loan)).all())

    def list_active_by_bicycle(self, bicycle_id: int) -> list[Loan]:
        statement = (
            select(Loan)
            .join(LoanBicycleLink, LoanBicycleLink.loan_id == Loan.id)
            .where(
                LoanBicycleLink.bicycle_id == bicycle_id,
                Loan.status == LoanStatus.in_progress,
            )
        )
        return list(self.session.exec(statement).all())

    def create(self, loan: Loan) -> Loan:
        self.session.add(loan)
        self.session.commit()
        self.session.refresh(loan)
        return loan

    def update(self, loan: Loan) -> Loan:
        self.session.add(loan)
        self.session.commit()
        self.session.refresh(loan)
        return loan
