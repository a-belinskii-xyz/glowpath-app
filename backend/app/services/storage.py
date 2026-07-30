from __future__ import annotations

from minio import Minio
from minio.error import S3Error

from app.config import settings
from app.core.errors import AppError


class StorageError(AppError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 500,
        params: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code, params=params)


class ObjectStorage:
    """Abstract object storage used for mood entry attachments."""

    def ensure_bucket(self) -> None:
        raise NotImplementedError

    def put_object(self, *, key: str, data: bytes, content_type: str) -> None:
        raise NotImplementedError

    def get_object(self, *, key: str) -> bytes:
        raise NotImplementedError

    def delete_object(self, *, key: str) -> None:
        raise NotImplementedError


class MinioStorage(ObjectStorage):
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ) -> None:
        self._bucket = bucket if bucket is not None else settings.minio_bucket
        self._client = Minio(
            endpoint if endpoint is not None else settings.minio_endpoint,
            access_key=access_key if access_key is not None else settings.minio_access_key,
            secret_key=secret_key if secret_key is not None else settings.minio_secret_key,
            secure=secure if secure is not None else settings.minio_secure,
        )
        self._bucket_ready = False

    def ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
        except S3Error as exc:
            raise StorageError(
                f"Failed to ensure bucket: {exc}", code="storage_bucket_failed"
            ) from exc
        self._bucket_ready = True

    def put_object(self, *, key: str, data: bytes, content_type: str) -> None:
        from io import BytesIO

        self.ensure_bucket()
        try:
            self._client.put_object(
                self._bucket,
                key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except S3Error as exc:
            raise StorageError(
                f"Failed to upload object: {exc}", code="storage_upload_failed"
            ) from exc

    def get_object(self, *, key: str) -> bytes:
        self.ensure_bucket()
        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as exc:
            raise StorageError(
                "Object not found", code="storage_object_not_found", status_code=404
            ) from exc
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, *, key: str) -> None:
        self.ensure_bucket()
        try:
            self._client.remove_object(self._bucket, key)
        except S3Error as exc:
            raise StorageError(
                f"Failed to delete object: {exc}", code="storage_delete_failed"
            ) from exc


class FakeStorage(ObjectStorage):
    """In-memory storage for tests."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    def ensure_bucket(self) -> None:
        return None

    def put_object(self, *, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = (data, content_type)

    def get_object(self, *, key: str) -> bytes:
        try:
            data, _content_type = self._objects[key]
        except KeyError as exc:
            raise StorageError(
                "Object not found", code="storage_object_not_found", status_code=404
            ) from exc
        return data

    def delete_object(self, *, key: str) -> None:
        self._objects.pop(key, None)

    def clear(self) -> None:
        self._objects.clear()


storage_service: ObjectStorage = MinioStorage()
