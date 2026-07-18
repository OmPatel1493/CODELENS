"""Object storage abstraction.

Routes and services depend on the `StorageBackend` interface, never on a concrete
cloud SDK (dependency inversion). Two implementations:

* `LocalStorageBackend` — writes under a local directory. Free, offline, no cloud
  account. The development default.
* `S3StorageBackend` — AWS S3 (or any S3-compatible store via a custom endpoint,
  e.g. MinIO). Used in deployment.

Switching is a single env var (`STORAGE_BACKEND`); no calling code changes. This
keeps day-to-day development at zero cost while supporting real S3 in production.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


class StorageBackend(ABC):
    """Minimal blob interface: save/load/exists/delete by string key."""

    @abstractmethod
    def save_bytes(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def load_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalStorageBackend(StorageBackend):
    """Filesystem-backed storage. Keys map to paths under a base directory."""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def _path(self, key: str) -> Path:
        # Guard against path traversal (e.g. keys containing "..").
        path = (self._base / key).resolve()
        if not str(path).startswith(str(self._base.resolve())):
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    def save_bytes(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def load_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3StorageBackend(StorageBackend):
    """AWS S3 (or S3-compatible) storage via boto3."""

    def __init__(
        self,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        endpoint_url: str = "",
    ) -> None:
        import boto3  # lazy: only imported when the S3 backend is actually used

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            endpoint_url=endpoint_url or None,
        )

    def save_bytes(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def load_bytes(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


@lru_cache
def get_storage() -> StorageBackend:
    """Return the configured storage backend (built once per process)."""
    if settings.STORAGE_BACKEND == "s3":
        if not settings.S3_BUCKET:
            raise RuntimeError("STORAGE_BACKEND=s3 requires S3_BUCKET to be set")
        return S3StorageBackend(
            bucket=settings.S3_BUCKET,
            region=settings.AWS_REGION,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )
    return LocalStorageBackend(settings.LOCAL_STORAGE_DIR)
