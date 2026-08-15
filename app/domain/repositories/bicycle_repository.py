from abc import ABC, abstractmethod

from app.domain.entities.bicycle import Bicycle


class BicycleRepository(ABC):
    @abstractmethod
    def get_by_id(self, bicycle_id: int) -> Bicycle | None: ...

    @abstractmethod
    def get_by_code(self, code: str) -> Bicycle | None: ...

    @abstractmethod
    def list_all(self) -> list[Bicycle]: ...

    @abstractmethod
    def create(self, bicycle: Bicycle) -> Bicycle: ...

    @abstractmethod
    def update(self, bicycle: Bicycle) -> Bicycle: ...

    @abstractmethod
    def delete(self, bicycle_id: int) -> None: ...
