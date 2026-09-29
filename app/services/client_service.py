from app.domain.repositories.client_repository import ClientRepository
from app.schemas.client import ClientRead


class ClientService:
    def __init__(self, client_repository: ClientRepository):
        self.client_repository = client_repository

    def get_by_document(self, document: str) -> ClientRead | None:
        client = self.client_repository.get_by_document(document)
        return ClientRead.model_validate(client) if client else None

    def search_by_document_prefix(self, prefix: str, limit: int = 10) -> list[ClientRead]:
        clients = self.client_repository.search_by_document_prefix(prefix, limit)
        return [ClientRead.model_validate(client) for client in clients]
