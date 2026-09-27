import uuid
from pathlib import Path

from google.cloud import storage

from app.domain.repositories.image_storage_repository import ImageStorageRepository


class GcsImageStorageRepository(ImageStorageRepository):
    def __init__(self, bucket_name: str):
        self._client = storage.Client()
        self._bucket_name = bucket_name

    def upload(self, *, bicycle_id: int, filename: str, content: bytes, content_type: str) -> str:
        extension = Path(filename).suffix
        blob_path = f"bicicletas/{bicycle_id}/{uuid.uuid4().hex}{extension}"
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(content, content_type=content_type)
        return blob_path
