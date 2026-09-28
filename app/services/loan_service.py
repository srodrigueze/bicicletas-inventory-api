from datetime import datetime, timezone

from app.domain.entities.audit_log import AuditAction
from app.domain.entities.bicycle import Bicycle
from app.domain.entities.client import Client
from app.domain.entities.loan import Loan, LoanDetail, LoanDetailStatus
from app.domain.entities.user import User
from app.domain.repositories.audit_repository import AuditRepository
from app.domain.repositories.bicycle_repository import BicycleRepository
from app.domain.repositories.client_repository import ClientRepository
from app.domain.repositories.loan_repository import LoanRepository
from app.schemas.client import ClientData, ClientRead
from app.schemas.loan import LoanCreate, LoanDetailRead, LoanRead
from app.services.audit_recording import record_audit


class LoanService:
    def __init__(
        self,
        loan_repository: LoanRepository,
        bicycle_repository: BicycleRepository,
        client_repository: ClientRepository,
        audit_repository: AuditRepository,
    ):
        self.loan_repository = loan_repository
        self.bicycle_repository = bicycle_repository
        self.client_repository = client_repository
        self.audit_repository = audit_repository

    def _to_read(self, loan: Loan) -> LoanRead:
        client = self.client_repository.get_by_id(loan.client_id)
        details = self.loan_repository.list_details_by_loan(loan.id)
        is_active = any(detail.status == LoanDetailStatus.on_loan for detail in details)
        return LoanRead(
            id=loan.id,
            client=ClientRead.model_validate(client),
            loan_datetime=loan.loan_datetime,
            is_active=is_active,
            details=[LoanDetailRead.model_validate(detail) for detail in details],
        )

    def _get_or_create_client(self, data: ClientData) -> Client:
        existing = self.client_repository.get_by_document(data.document)
        if not existing:
            return self.client_repository.create(
                Client(full_name=data.full_name, document=data.document, phone=data.phone)
            )
        if existing.full_name != data.full_name or existing.phone != data.phone:
            existing.full_name = data.full_name
            existing.phone = data.phone
            existing = self.client_repository.update(existing)
        return existing

    def _validate_bicycle_available(self, bicycle_id: int) -> Bicycle:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        if not bicycle:
            raise ValueError(f"Bicycle {bicycle_id} does not exist")
        if not bicycle.en_posesion_jac:
            raise ValueError(f"Bicycle {bicycle.code} is not in possession of the JAC")
        if self.loan_repository.get_active_detail_by_bicycle(bicycle_id):
            raise ValueError(f"Bicycle {bicycle.code} is already on an active loan")
        return bicycle

    def list_loans(self, *, active_only: bool = True, skip: int = 0, limit: int = 50) -> list[LoanRead]:
        if active_only:
            loans = self.loan_repository.list_active(skip=skip, limit=limit)
        else:
            loans = self.loan_repository.list_all(skip=skip, limit=limit)
        return [self._to_read(loan) for loan in loans]

    def get_loan(self, loan_id: int) -> LoanRead | None:
        loan = self.loan_repository.get_by_id(loan_id)
        return self._to_read(loan) if loan else None

    def create_loan(self, acting_user: User, data: LoanCreate) -> LoanRead:
        client = self._get_or_create_client(data.client)
        bicycles = [self._validate_bicycle_available(bicycle_id) for bicycle_id in data.bicycle_ids]

        loan = Loan(client_id=client.id, loan_datetime=datetime.now(timezone.utc))
        created_loan = self.loan_repository.create(loan)

        details = [
            self.loan_repository.add_detail(LoanDetail(loan_id=created_loan.id, bicycle_id=bicycle.id))
            for bicycle in bicycles
        ]

        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.create,
            entity_name="Loan",
            entity_id=created_loan.id,
            previous_values=None,
            new_values={
                "loan": created_loan.model_dump(mode="json"),
                "details": [detail.model_dump(mode="json") for detail in details],
            },
        )
        return self._to_read(created_loan)

    def return_detail(self, acting_user: User, loan_id: int, detail_id: int) -> LoanRead:
        loan = self.loan_repository.get_by_id(loan_id)
        if not loan:
            raise ValueError(f"Loan {loan_id} does not exist")
        detail = self.loan_repository.get_detail_by_id(detail_id)
        if not detail or detail.loan_id != loan_id:
            raise ValueError(f"Loan detail {detail_id} does not belong to loan {loan_id}")
        if detail.status != LoanDetailStatus.on_loan:
            raise ValueError(f"Loan detail {detail_id} is already returned")

        previous_snapshot = detail.model_dump(mode="json")
        detail.status = LoanDetailStatus.returned
        detail.returned_at = datetime.now(timezone.utc)
        updated_detail = self.loan_repository.update_detail(detail)

        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.returned,
            entity_name="Loan",
            entity_id=loan_id,
            previous_values=previous_snapshot,
            new_values=updated_detail.model_dump(mode="json"),
        )
        return self._to_read(loan)

    def swap_bicycle(self, acting_user: User, loan_id: int, detail_id: int, new_bicycle_id: int) -> LoanRead:
        loan = self.loan_repository.get_by_id(loan_id)
        if not loan:
            raise ValueError(f"Loan {loan_id} does not exist")
        detail = self.loan_repository.get_detail_by_id(detail_id)
        if not detail or detail.loan_id != loan_id:
            raise ValueError(f"Loan detail {detail_id} does not belong to loan {loan_id}")
        if detail.status != LoanDetailStatus.on_loan:
            raise ValueError(f"Loan detail {detail_id} is already returned")

        new_bicycle = self._validate_bicycle_available(new_bicycle_id)

        previous_snapshot = detail.model_dump(mode="json")
        detail.status = LoanDetailStatus.returned
        detail.returned_at = datetime.now(timezone.utc)
        self.loan_repository.update_detail(detail)

        new_detail = self.loan_repository.add_detail(LoanDetail(loan_id=loan_id, bicycle_id=new_bicycle.id))

        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.swap,
            entity_name="Loan",
            entity_id=loan_id,
            previous_values=previous_snapshot,
            new_values=new_detail.model_dump(mode="json"),
        )
        return self._to_read(loan)
