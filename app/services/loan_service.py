from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.core.timezone import day_bounds_utc
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

    def _add_detail_or_conflict(self, loan_id: int, bicycle_id: int) -> LoanDetail:
        try:
            return self.loan_repository.add_detail(LoanDetail(loan_id=loan_id, bicycle_id=bicycle_id))
        except IntegrityError as exc:
            # The app-level availability check passed, but a concurrent
            # request beat us to it and the DB's unique index rejected this
            # insert — translate it into the same conflict signal used for
            # the ordinary "not available" case.
            raise ValueError(f"Bicycle {bicycle_id} is already on an active loan") from exc

    def _validate_bicycle_available(self, bicycle_id: int) -> Bicycle:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        if not bicycle:
            raise ValueError(f"Bicycle {bicycle_id} does not exist")
        if not bicycle.en_posesion_jac:
            raise ValueError(f"Bicycle {bicycle.code} is not in possession of the JAC")
        if self.loan_repository.get_active_detail_by_bicycle(bicycle_id):
            raise ValueError(f"Bicycle {bicycle.code} is already on an active loan")
        return bicycle

    def list_loans(
        self,
        *,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[LoanRead]:
        # The "Activos" tab (HU-16) always means exactly this, regardless of
        # whatever status/date filters are also present in the request —
        # status/date are only meaningful for the "Todos" view.
        if active_only:
            loans = self.loan_repository.list_active(skip=skip, limit=limit)
            return [self._to_read(loan) for loan in loans]

        # Same "a single date filters that one day" convention as audits (RNG-22).
        if start_date and not end_date:
            end_date = start_date
        elif end_date and not start_date:
            start_date = end_date

        start_datetime = day_bounds_utc(start_date)[0] if start_date else None
        end_datetime = day_bounds_utc(end_date)[1] if end_date else None

        loans = self.loan_repository.list_filtered(
            skip=skip,
            limit=limit,
            status=status,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        return [self._to_read(loan) for loan in loans]

    def get_loan(self, loan_id: int) -> LoanRead | None:
        loan = self.loan_repository.get_by_id(loan_id)
        return self._to_read(loan) if loan else None

    def create_loan(self, acting_user: User, data: LoanCreate) -> LoanRead:
        client = self._get_or_create_client(data.client)
        if self.loan_repository.get_active_loan_by_client_id(client.id):
            raise ValueError(
                f"Client {client.document} already has an active loan; "
                "add bicycles to it instead of creating a new one"
            )
        bicycles = [self._validate_bicycle_available(bicycle_id) for bicycle_id in data.bicycle_ids]

        loan = Loan(client_id=client.id, loan_datetime=datetime.now(timezone.utc))
        created_loan = self.loan_repository.create(loan)

        details = [self._add_detail_or_conflict(created_loan.id, bicycle.id) for bicycle in bicycles]

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
        if detail.status not in (LoanDetailStatus.on_loan, LoanDetailStatus.incumplido):
            raise ValueError(f"Loan detail {detail_id} is already returned")

        # A late return of a bicycle previously marked incumplido hands the
        # JAC back its possession of it — reverse of what mark_incumplido did.
        was_incumplido = detail.status == LoanDetailStatus.incumplido

        previous_snapshot = detail.model_dump(mode="json")
        detail.status = LoanDetailStatus.returned
        detail.returned_at = datetime.now(timezone.utc)
        updated_detail = self.loan_repository.update_detail(detail)

        if was_incumplido:
            bicycle = self.bicycle_repository.get_by_id(updated_detail.bicycle_id)
            bicycle_previous_snapshot = bicycle.model_dump(mode="json")
            bicycle.en_posesion_jac = True
            updated_bicycle = self.bicycle_repository.update(bicycle)
            record_audit(
                self.audit_repository,
                user=acting_user,
                action=AuditAction.restore,
                entity_name="Bicycle",
                entity_id=updated_bicycle.id,
                previous_values=bicycle_previous_snapshot,
                new_values=updated_bicycle.model_dump(mode="json"),
            )

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

    def mark_incumplido(self, acting_user: User, loan_id: int, detail_id: int) -> LoanRead:
        loan = self.loan_repository.get_by_id(loan_id)
        if not loan:
            raise ValueError(f"Loan {loan_id} does not exist")
        detail = self.loan_repository.get_detail_by_id(detail_id)
        if not detail or detail.loan_id != loan_id:
            raise ValueError(f"Loan detail {detail_id} does not belong to loan {loan_id}")
        if detail.status != LoanDetailStatus.on_loan:
            raise ValueError(f"Loan detail {detail_id} cannot be marked incumplido from its current status")

        previous_snapshot = detail.model_dump(mode="json")
        detail.status = LoanDetailStatus.incumplido
        updated_detail = self.loan_repository.update_detail(detail)

        # The JAC no longer has the bicycle in its possession — same
        # consequence as a logical delete (RN-REQ002-07), triggered manually
        # here instead of through the bicycle endpoint.
        bicycle = self.bicycle_repository.get_by_id(updated_detail.bicycle_id)
        bicycle_previous_snapshot = bicycle.model_dump(mode="json")
        bicycle.en_posesion_jac = False
        updated_bicycle = self.bicycle_repository.update(bicycle)

        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.incumplido,
            entity_name="Loan",
            entity_id=loan_id,
            previous_values=previous_snapshot,
            new_values=updated_detail.model_dump(mode="json"),
        )
        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.delete,
            entity_name="Bicycle",
            entity_id=updated_bicycle.id,
            previous_values=bicycle_previous_snapshot,
            new_values=updated_bicycle.model_dump(mode="json"),
        )
        return self._to_read(loan)

    def add_bicycles(self, acting_user: User, loan_id: int, bicycle_ids: list[int]) -> LoanRead:
        loan = self.loan_repository.get_by_id(loan_id)
        if not loan:
            raise ValueError(f"Loan {loan_id} does not exist")

        bicycles = [self._validate_bicycle_available(bicycle_id) for bicycle_id in bicycle_ids]
        details = [self._add_detail_or_conflict(loan_id, bicycle.id) for bicycle in bicycles]

        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.add_bicycle,
            entity_name="Loan",
            entity_id=loan_id,
            previous_values=None,
            new_values={"details": [detail.model_dump(mode="json") for detail in details]},
        )
        return self._to_read(loan)
