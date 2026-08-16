from app.domain.entities.bicycle import Bicycle, BicycleCondition, BicycleSize
from app.domain.repositories.bicycle_repository import BicycleRepository
from app.domain.repositories.loan_repository import LoanRepository
from app.schemas.bicycle import BicycleCreate, BicycleRead, BicycleUpdate


class BicycleService:
    def __init__(
        self,
        bicycle_repository: BicycleRepository,
        loan_repository: LoanRepository,
    ):
        self.bicycle_repository = bicycle_repository
        self.loan_repository = loan_repository

    def _is_available(self, bicycle: Bicycle) -> bool:
        if not bicycle.en_posesion_jac:
            return False
        return not self.loan_repository.list_active_by_bicycle(bicycle.id)

    def _to_read(self, bicycle: Bicycle) -> BicycleRead:
        return BicycleRead(**bicycle.model_dump(), is_available=self._is_available(bicycle))

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
            en_posesion_jac=en_posesion_jac,
        )
        return [self._to_read(bicycle) for bicycle in bicycles]

    def get_bicycle(self, bicycle_id: int) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        return self._to_read(bicycle) if bicycle else None

    def create_bicycle(self, data: BicycleCreate) -> BicycleRead:
        if self.bicycle_repository.get_by_code(data.code):
            raise ValueError(f"A bicycle with code '{data.code}' already exists")
        
        bicycle = Bicycle(**data.model_dump(), en_posesion_jac=True)
        created = self.bicycle_repository.create(bicycle)
        return self._to_read(created)

    def update_bicycle(self, bicycle_id: int, data: BicycleUpdate) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)

        if not bicycle:
            return None
        
        updates = data.model_dump(exclude_unset=True)

        if "code" in updates and updates["code"] != bicycle.code:
            existing = self.bicycle_repository.get_by_code(updates["code"])

            if existing and existing.id != bicycle_id:
                raise ValueError(f"A bicycle with code '{updates['code']}' already exists")

            
        for field, value in updates.items():
            setattr(bicycle, field, value)

        updated = self.bicycle_repository.update(bicycle)
        return self._to_read(updated)

    def delete_bicycle(self, bicycle_id: int) -> BicycleRead | None:
        bicycle = self.bicycle_repository.delete(bicycle_id)
        return self._to_read(bicycle) if bicycle else None

    def restore_bicycle(self, bicycle_id: int) -> BicycleRead | None:
        bicycle = self.bicycle_repository.restore(bicycle_id)
        return self._to_read(bicycle) if bicycle else None
