from app.domain.entities.bicycle import Bicycle, BicycleCondition
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
        if bicycle.condition != BicycleCondition.good:
            return False
        return not self.loan_repository.list_active_by_bicycle(bicycle.id)

    def _to_read(self, bicycle: Bicycle) -> BicycleRead:
        return BicycleRead(**bicycle.model_dump(), is_available=self._is_available(bicycle))

    def list_bicycles(self) -> list[BicycleRead]:
        return [self._to_read(bicycle) for bicycle in self.bicycle_repository.list_all()]

    def get_bicycle(self, bicycle_id: int) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        return self._to_read(bicycle) if bicycle else None

    def create_bicycle(self, data: BicycleCreate) -> BicycleRead:
        if self.bicycle_repository.get_by_code(data.code):
            raise ValueError(f"A bicycle with code '{data.code}' already exists")
        bicycle = Bicycle(**data.model_dump())
        created = self.bicycle_repository.create(bicycle)
        return self._to_read(created)

    def update_bicycle(self, bicycle_id: int, data: BicycleUpdate) -> BicycleRead | None:
        bicycle = self.bicycle_repository.get_by_id(bicycle_id)
        if not bicycle:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(bicycle, field, value)
        updated = self.bicycle_repository.update(bicycle)
        return self._to_read(updated)

    def delete_bicycle(self, bicycle_id: int) -> None:
        self.bicycle_repository.delete(bicycle_id)
