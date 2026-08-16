from sqlmodel import Session, select

from app.domain.entities.bicycle import Bicycle, BicycleCondition, BicycleSize
from app.domain.repositories.bicycle_repository import BicycleRepository


class SqlBicycleRepository(BicycleRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, bicycle_id: int) -> Bicycle | None:
        return self.session.get(Bicycle, bicycle_id)

    def get_by_code(self, code: str) -> Bicycle | None:
        statement = select(Bicycle).where(Bicycle.code == code)
        return self.session.exec(statement).first()

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
    ) -> list[Bicycle]:
        statement = select(Bicycle)
        if code:
            statement = statement.where(Bicycle.code.ilike(f"%{code}%"))
        if size is not None:
            statement = statement.where(Bicycle.size == size)
        if condition is not None:
            statement = statement.where(Bicycle.condition == condition)
        if rueditas_asistencia is not None:
            statement = statement.where(Bicycle.rueditas_asistencia == rueditas_asistencia)
        if tiene_pedales is not None:
            statement = statement.where(Bicycle.tiene_pedales == tiene_pedales)
        if en_posesion_jac is not None:
            statement = statement.where(Bicycle.en_posesion_jac == en_posesion_jac)
        statement = statement.offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def create(self, bicycle: Bicycle) -> Bicycle:
        self.session.add(bicycle)
        self.session.commit()
        self.session.refresh(bicycle)
        return bicycle

    def update(self, bicycle: Bicycle) -> Bicycle:
        self.session.add(bicycle)
        self.session.commit()
        self.session.refresh(bicycle)
        return bicycle

    def delete(self, bicycle_id: int) -> Bicycle | None:
        bicycle = self.session.get(Bicycle, bicycle_id)
        if not bicycle:
            return None
        bicycle.en_posesion_jac = False
        self.session.add(bicycle)
        self.session.commit()
        self.session.refresh(bicycle)
        return bicycle

    def restore(self, bicycle_id: int) -> Bicycle | None:
        bicycle = self.session.get(Bicycle, bicycle_id)
        if not bicycle:
            return None
        bicycle.en_posesion_jac = True
        self.session.add(bicycle)
        self.session.commit()
        self.session.refresh(bicycle)
        return bicycle
