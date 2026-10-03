from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.loan import Loan, LoanDetail


class LoanRepository(ABC):
    @abstractmethod
    def get_by_id(self, loan_id: int) -> Loan | None: ...

    @abstractmethod
    def list_all(self, *, skip: int = 0, limit: int = 50) -> list[Loan]: ...

    @abstractmethod
    def list_by_date_range(self, start_datetime: datetime, end_datetime: datetime) -> list[Loan]: ...

    @abstractmethod
    def list_active(self, *, skip: int = 0, limit: int = 50) -> list[Loan]: ...

    @abstractmethod
    def list_filtered(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
    ) -> list[Loan]:
        """status, when given, is one of 'activo' | 'incumplido' | 'cerrado' —
        derived from the loan's details, not a stored column."""
        ...

    @abstractmethod
    def get_active_loan_by_client_id(self, client_id: int) -> Loan | None: ...

    @abstractmethod
    def create(self, loan: Loan) -> Loan: ...

    @abstractmethod
    def list_details_by_loan(self, loan_id: int) -> list[LoanDetail]: ...

    @abstractmethod
    def get_detail_by_id(self, detail_id: int) -> LoanDetail | None: ...

    @abstractmethod
    def add_detail(self, detail: LoanDetail) -> LoanDetail: ...

    @abstractmethod
    def update_detail(self, detail: LoanDetail) -> LoanDetail: ...

    @abstractmethod
    def get_active_detail_by_bicycle(self, bicycle_id: int) -> LoanDetail | None: ...
