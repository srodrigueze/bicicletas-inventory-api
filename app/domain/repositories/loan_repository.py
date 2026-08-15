from abc import ABC, abstractmethod

from app.domain.entities.loan import Loan


class LoanRepository(ABC):
    @abstractmethod
    def get_by_id(self, loan_id: int) -> Loan | None: ...

    @abstractmethod
    def list_all(self) -> list[Loan]: ...

    @abstractmethod
    def list_active_by_bicycle(self, bicycle_id: int) -> list[Loan]: ...

    @abstractmethod
    def create(self, loan: Loan) -> Loan: ...

    @abstractmethod
    def update(self, loan: Loan) -> Loan: ...
