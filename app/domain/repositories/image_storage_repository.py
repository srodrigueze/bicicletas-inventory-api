from abc import ABC, abstractmethod


class ImageStorageRepository(ABC):
    @abstractmethod
    def upload(self, *, bicycle_id: int, filename: str, content: bytes, content_type: str) -> str:
        """Uploads the file and returns the relative path it was stored under."""
        ...
