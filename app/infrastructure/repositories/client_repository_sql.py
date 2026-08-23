from sqlmodel import Session, select

from app.domain.entities.client import Client
from app.domain.repositories.client_repository import ClientRepository


class SqlClientRepository(ClientRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, client_id: int) -> Client | None:
        return self.session.get(Client, client_id)

    def get_by_document(self, document: str) -> Client | None:
        statement = select(Client).where(Client.document == document)
        return self.session.exec(statement).first()

    def create(self, client: Client) -> Client:
        self.session.add(client)
        self.session.commit()
        self.session.refresh(client)
        return client
