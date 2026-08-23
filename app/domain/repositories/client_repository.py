from abc import ABC, abstractmethod

from app.domain.entities.client import Client


class ClientRepository(ABC):
    @abstractmethod
    def get_by_id(self, client_id: int) -> Client | None: ...

    @abstractmethod
    def get_by_document(self, document: str) -> Client | None: ...

    @abstractmethod
    def create(self, client: Client) -> Client: ...
