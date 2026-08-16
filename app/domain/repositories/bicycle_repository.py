from abc import ABC, abstractmethod

from app.domain.entities.bicycle import Bicycle, BicycleCondition, BicycleSize


class BicycleRepository(ABC):
    @abstractmethod
    def get_by_id(self, bicycle_id: int) -> Bicycle | None: ...

    @abstractmethod
    def get_by_code(self, code: str) -> Bicycle | None: ...

    @abstractmethod
    def list_all(
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
    ) -> list[Bicycle]: ...

    @abstractmethod
    def create(self, bicycle: Bicycle) -> Bicycle: ...

    @abstractmethod
    def update(self, bicycle: Bicycle) -> Bicycle: ...

    @abstractmethod
    def delete(self, bicycle_id: int) -> Bicycle | None:
        """Logical delete only (RNG-13/RN-REQ002-05): sets en_posesion_jac to
        False and persists it. Never issues a physical DELETE. Returns the
        updated bicycle, or None if it doesn't exist."""
        ...

    @abstractmethod
    def restore(self, bicycle_id: int) -> Bicycle | None:
        """Reverses a logical delete (RN-REQ002-06/HU-10): sets
        en_posesion_jac back to True. Returns the updated bicycle, or None if
        it doesn't exist."""
        ...
