from datetime import datetime

from app.domain.entities.bicycle import BicycleCondition
from app.domain.entities.loan import Loan, LoanStatus
from app.domain.repositories.bicycle_repository import BicycleRepository
from app.domain.repositories.loan_repository import LoanRepository
from app.schemas.loan import LoanCreate, LoanRead


class LoanService:
    def __init__(
        self,
        loan_repository: LoanRepository,
        bicycle_repository: BicycleRepository,
    ):
        self.loan_repository = loan_repository
        self.bicycle_repository = bicycle_repository

    def _to_read(self, loan: Loan) -> LoanRead:
        return LoanRead(
            **loan.model_dump(),
            bicycle_ids=[bicycle.id for bicycle in loan.bicycles],
        )

    def list_loans(self) -> list[LoanRead]:
        return [self._to_read(loan) for loan in self.loan_repository.list_all()]

    def get_loan(self, loan_id: int) -> LoanRead | None:
        loan = self.loan_repository.get_by_id(loan_id)
        return self._to_read(loan) if loan else None

    def create_loan(self, data: LoanCreate) -> LoanRead:
        bicycles = []
        for bicycle_id in data.bicycle_ids:
            bicycle = self.bicycle_repository.get_by_id(bicycle_id)
            if not bicycle:
                raise ValueError(f"Bicycle {bicycle_id} does not exist")
            if bicycle.condition != BicycleCondition.good:
                raise ValueError(f"Bicycle {bicycle.code} is not in good condition")
            if self.loan_repository.list_active_by_bicycle(bicycle_id):
                raise ValueError(f"Bicycle {bicycle.code} is already on an active loan")
            bicycles.append(bicycle)

        loan = Loan(
            requester_name=data.requester_name,
            id_document=data.id_document,
            phone=data.phone,
            loan_datetime=data.loan_datetime,
            status=LoanStatus.in_progress,
            bicycles=bicycles,
        )
        created = self.loan_repository.create(loan)
        return self._to_read(created)

    def return_loan(self, loan_id: int, return_datetime: datetime) -> LoanRead | None:
        loan = self.loan_repository.get_by_id(loan_id)
        if not loan:
            return None
        loan.return_datetime = return_datetime
        loan.status = LoanStatus.finished
        updated = self.loan_repository.update(loan)
        return self._to_read(updated)
