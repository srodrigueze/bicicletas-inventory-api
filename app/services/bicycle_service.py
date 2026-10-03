from app.core.config import settings
from app.domain.entities.audit_log import AuditAction
from app.domain.entities.bicycle import Bicycle, BicycleCondition, BicycleSize
from app.domain.entities.user import User
from app.domain.repositories.audit_repository import AuditRepository
from app.domain.repositories.bicycle_repository import BicycleRepository
from app.domain.repositories.image_storage_repository import ImageStorageRepository
from app.domain.repositories.loan_repository import LoanRepository
from app.schemas.bicycle import BicycleCreate, BicycleRead, BicycleUpdate
from app.services.audit_recording import record_audit


class BicycleService:
    def __init__(
        self,
        bicycle_repository: BicycleRepository,
        loan_repository: LoanRepository,
        audit_repository: AuditRepository,
        image_storage_repository: ImageStorageRepository,
    ):
        self.bicycle_repository = bicycle_repository
        self.loan_repository = loan_repository
        self.audit_repository = audit_repository
        self.image_storage_repository = image_storage_repository

    def _is_available(self, bicycle: Bicycle) -> bool:
        if not bicycle.en_posesion_jac:
            return False
        return self.loan_repository.get_active_detail_by_bicycle(bicycle.id) is None

    def _image_url(self, bicycle: Bicycle) -> str | None:
        if not bicycle.image_path:
            return None
        return f"{settings.image_base_url}{bicycle.image_path}"

    def _to_read(self, bicycle: Bicycle) -> BicycleRead:
        return BicycleRead(
            **bicycle.model_dump(),
            is_available=self._is_available(bicycle),
            image_url=self._image_url(bicycle),
        )

    def list_bicycles(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        code: str | None = None,
        size: BicycleSize | None = None,
        condition: BicycleCondition | None = None,
        rueditas_asistencia: bool | None = None,
        tiene_pedales: bool | None = None,
        numero_frenos: int | None = None,
        en_posesion_jac: bool | None = None,
    ) -> list[BicycleRead]:
        bicycles = self.bicycle_repository.list_all(
            skip=skip,
            limit=limit,
            code=code,
            size=size,
            condition=condition,
            rueditas_asistencia=rueditas_asistencia,
            tiene_pedales=tiene_pedales,
            numero_frenos=numero_frenos,
            en_posesion_jac=en_posesion_jac,
        )
        return [self._to_read(bicycle) for bicycle in bicycles]

    def get_bicycle(self, bicycle_id: int) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        return self._to_read(bicycle) if bicycle else None

    def create_bicycle(self, acting_user: User, data: BicycleCreate) -> BicycleRead:
        if self.bicycle_repository.get_by_code(data.code):
            raise ValueError(f"A bicycle with code '{data.code}' already exists")
        bicycle = Bicycle(**data.model_dump(), en_posesion_jac=True)
        created = self.bicycle_repository.create(bicycle)
        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.create,
            entity_name="Bicycle",
            entity_id=created.id,
            previous_values=None,
            new_values=created.model_dump(mode="json"),
        )
        return self._to_read(created)

    def update_bicycle(self, acting_user: User, bicycle_id: int, data: BicycleUpdate) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        if not bicycle:
            return None
        updates = data.model_dump(exclude_unset=True)
        if "code" in updates and updates["code"] != bicycle.code:
            existing = self.bicycle_repository.get_by_code(updates["code"])
            if existing and existing.id != bicycle_id:
                raise ValueError(f"A bicycle with code '{updates['code']}' already exists")
        previous_snapshot = bicycle.model_dump(mode="json")
        for field, value in updates.items():
            setattr(bicycle, field, value)
        updated = self.bicycle_repository.update(bicycle)
        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.update,
            entity_name="Bicycle",
            entity_id=updated.id,
            previous_values=previous_snapshot,
            new_values=updated.model_dump(mode="json"),
        )
        return self._to_read(updated)

    def delete_bicycle(self, acting_user: User, bicycle_id: int) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        if not bicycle:
            return None
        previous_snapshot = bicycle.model_dump(mode="json")
        deleted = self.bicycle_repository.delete(bicycle_id)
        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.delete,
            entity_name="Bicycle",
            entity_id=deleted.id,
            previous_values=previous_snapshot,
            new_values=deleted.model_dump(mode="json"),
        )
        return self._to_read(deleted)

    def restore_bicycle(self, acting_user: User, bicycle_id: int) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        if not bicycle:
            return None
        previous_snapshot = bicycle.model_dump(mode="json")
        restored = self.bicycle_repository.restore(bicycle_id)
        record_audit(
            self.audit_repository,
            user=acting_user,
            action=AuditAction.restore,
            entity_name="Bicycle",
            entity_id=restored.id,
            previous_values=previous_snapshot,
            new_values=restored.model_dump(mode="json"),
        )
        return self._to_read(restored)

    def upload_image(
        self, acting_user: User, bicycle_id: int, filename: str, content: bytes, content_type: str
    ) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        if not bicycle:
            return None
        image_path = self.image_storage_repository.upload(
            bicycle_id=bicycle_id, filename=filename, content=content, content_type=content_type
        )
        return self.update_bicycle(acting_user, bicycle_id, BicycleUpdate(image_path=image_path))
