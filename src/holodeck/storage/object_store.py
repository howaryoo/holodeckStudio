from __future__ import annotations

from typing import Protocol



class ObjectStore(Protocol):
    async def put(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        ...

    async def get(self, bucket: str, key: str) -> bytes:
        ...

    async def list(self, bucket: str, prefix: str = "") -> list[str]:
        ...

    async def delete(self, bucket: str, key: str) -> None:
        ...


from minio import Minio


class MinIOObjectStore:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
    ) -> None:
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    async def put(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        import io

        self._client._ensure_bucket_exists(bucket)
        self._client.put_object(
            bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"{bucket}/{key}"

    async def get(self, bucket: str, key: str) -> bytes:
        response = self._client.get_object(bucket, key)
        data = response.read()
        response.close()
        response.release_conn()
        return data

    async def list(self, bucket: str, prefix: str = "") -> list[str]:
        objects = self._client.list_objects(bucket, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]

    async def delete(self, bucket: str, key: str) -> None:
        self._client.remove_object(bucket, key)