from abc import ABC, abstractmethod

from app.domain.entities.client import Client


class ClientRepository(ABC):
    @abstractmethod
    def get_by_id(self, client_id: int) -> Client | None: ...

    @abstractmethod
    def get_by_document(self, document: str) -> Client | None: ...

    @abstractmethod
    def search_by_document_prefix(self, prefix: str, limit: int) -> list[Client]: ...

    @abstractmethod
    def create(self, client: Client) -> Client: ...

    @abstractmethod
    def update(self, client: Client) -> Client: ...
