"""File storage behind one interface; STORAGE_BACKEND picks the implementation.

Keys look like "cvs/<user_id>/<file>" and "recordings/<user_id>/<session_id>.webm". Adding S3 = one more
BlobStore subclass (put/get/delete/signed_url) and a branch in get_storage."""

from datetime import UTC, datetime, timedelta

import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions, ContentSettings, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient

from server.adapters.http_client import shared_client
from server.config import Settings


class BlobStore(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def signed_url(self, key: str, expires_s: int = 3600) -> str:
        """Time-limited URL a browser can fetch the file from directly (e.g. recording replay)."""


class SupabaseStore(BlobStore):
    """Supabase Storage, one private bucket, service-role key (server only)."""

    def __init__(self, url: str, service_key: str, bucket: str):
        self._base = f"{url.rstrip('/')}/storage/v1"
        self._bucket = bucket
        self._headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}

    def _object(self, key: str) -> str:
        return f"{self._base}/object/{self._bucket}/{quote(key)}"

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        r = await shared_client().post(
            self._object(key), content=data, headers=self._headers | {"Content-Type": content_type, "x-upsert": "true"}
        )
        r.raise_for_status()

    async def get(self, key: str) -> bytes:
        r = await shared_client().get(self._object(key), headers=self._headers)
        r.raise_for_status()
        return r.content

    async def delete(self, key: str) -> None:
        r = await shared_client().request(
            "DELETE", f"{self._base}/object/{self._bucket}", json={"prefixes": [key]}, headers=self._headers
        )
        r.raise_for_status()

    async def signed_url(self, key: str, expires_s: int = 3600) -> str:
        r = await shared_client().post(
            f"{self._base}/object/sign/{self._bucket}/{quote(key)}", json={"expiresIn": expires_s}, headers=self._headers
        )
        r.raise_for_status()
        return f"{self._base}{r.json()['signedURL']}"


class AzureBlobStore(BlobStore):
    """Azure Blob Storage, one private container, account connection string (server only).
    Signed URLs are read-only SAS links to a single blob."""

    def __init__(self, connection_string: str, container: str):
        self._service = BlobServiceClient.from_connection_string(connection_string)
        self._container = self._service.get_container_client(container)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await self._container.upload_blob(
            key, data, overwrite=True, content_settings=ContentSettings(content_type=content_type)
        )

    async def get(self, key: str) -> bytes:
        return await (await self._container.download_blob(key)).readall()

    async def delete(self, key: str) -> None:
        try:
            await self._container.delete_blob(key)
        except ResourceNotFoundError:
            pass

    async def signed_url(self, key: str, expires_s: int = 3600) -> str:
        blob = self._container.get_blob_client(key)
        sas = generate_blob_sas(
            account_name=self._service.account_name,
            container_name=self._container.container_name,
            blob_name=key,
            account_key=self._service.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(UTC) + timedelta(seconds=expires_s),
        )
        return f"{blob.url}?{sas}"


class LocalStore(BlobStore):
    """Files on local disk, for development and tests. Signed URLs point at the gateway's /files route,
    which checks an HMAC signature and expiry (see `verify`)."""

    def __init__(self, root: str, secret: str, public_base: str):
        self._root = Path(root).resolve()
        self._secret = secret.encode()
        self._public_base = public_base.rstrip("/")

    def path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root):  # "../" in a key must not escape the store
            raise ValueError(f"bad storage key {key!r}")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def get(self, key: str) -> bytes:
        return self.path(key).read_bytes()

    async def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)

    def _sig(self, key: str, exp: int) -> str:
        return hmac.new(self._secret, f"{key}:{exp}".encode(), hashlib.sha256).hexdigest()

    async def signed_url(self, key: str, expires_s: int = 3600) -> str:
        exp = int(time.time()) + expires_s
        return f"{self._public_base}/files/{quote(key)}?exp={exp}&sig={self._sig(key, exp)}"

    def verify(self, key: str, exp: int, sig: str) -> bool:
        return exp > time.time() and hmac.compare_digest(sig, self._sig(key, exp))


_store: BlobStore | None = None


def get_storage(settings: Settings) -> BlobStore:
    global _store
    if _store is None:
        if settings.storage_backend == "azure":
            if not settings.azure_storage_connection_string:
                raise ValueError("STORAGE_BACKEND=azure needs AZURE_STORAGE_CONNECTION_STRING")
            _store = AzureBlobStore(settings.azure_storage_connection_string, settings.storage_bucket)
        elif settings.storage_backend == "supabase":
            if not (settings.supabase_url and settings.supabase_service_role_key):
                raise ValueError("STORAGE_BACKEND=supabase needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
            _store = SupabaseStore(settings.supabase_url, settings.supabase_service_role_key, settings.storage_bucket)
        elif settings.storage_backend == "local":
            _store = LocalStore(settings.local_storage_dir, settings.files_secret, settings.public_base_url)
        else:
            raise ValueError(f"Unknown STORAGE_BACKEND: {settings.storage_backend}")
    return _store
