from sqlmodel import Session, select

from app.domain.entities.bicycle import Bicycle
from app.domain.repositories.bicycle_repository import BicycleRepository


class SqlBicycleRepository(BicycleRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, bicycle_id: int) -> Bicycle | None:
        return self.session.get(Bicycle, bicycle_id)

    def get_by_code(self, code: str) -> Bicycle | None:
        statement = select(Bicycle).where(Bicycle.code == code)
        return self.session.exec(statement).first()

    def list_all(self) -> list[Bicycle]:
        return list(self.session.exec(select(Bicycle)).all())

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

    def delete(self, bicycle_id: int) -> None:
        bicycle = self.session.get(Bicycle, bicycle_id)
        if bicycle:
            self.session.delete(bicycle)
            self.session.commit()
