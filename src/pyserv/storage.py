"""
Storage backends for Pyserv  framework.
Provides multiple storage options including local, S3, GCS, and Azure.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Dict, List, AsyncGenerator
from pathlib import Path
import aiofiles
import aiohttp
from google.cloud import storage as gcs
from azure.storage.blob import BlobServiceClient
import boto3
from botocore.config import Config

class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    async def put(self, key: str, data: BinaryIO, metadata: Dict = None) -> str:
        """Store data with given key"""
        pass

    @abstractmethod
    async def get(self, key: str) -> BinaryIO:
        """Retrieve data by key"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete data by key"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass

    @abstractmethod
    async def list(self, prefix: str = "") -> List[str]:
        """List keys with optional prefix"""
        pass

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get URL for accessing the data"""
        pass

class LocalStorage(StorageBackend):
    """Local filesystem storage backend"""

    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    async def put(self, key: str, data: BinaryIO, metadata: Dict = None) -> str:
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := data.read(8192):
                await f.write(chunk)
        return str(file_path)

    async def get(self, key: str) -> BinaryIO:
        file_path = self.base_path / key
        return await aiofiles.open(file_path, 'rb')

    async def delete(self, key: str) -> bool:
        file_path = self.base_path / key
        try:
            file_path.unlink()
            return True
        except FileNotFoundError:
            return False

    async def exists(self, key: str) -> bool:
        return (self.base_path / key).exists()

    async def list(self, prefix: str = "") -> List[str]:
        path = self.base_path / prefix
        if path.is_file():
            return [str(path.relative_to(self.base_path))]
        return [str(p.relative_to(self.base_path)) for p in path.rglob('*') if p.is_file()]

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/files/{key}"

class S3Storage(StorageBackend):
    """Amazon S3 storage backend"""

    def __init__(self, bucket_name: str, region: str = "us-east-1",
                 access_key: str = None, secret_key: str = None):
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                region_name=region,
                retries={'max_attempts': 3, 'mode': 'standard'}
            )
        )

    async def put(self, key: str, data: BinaryIO, metadata: Dict = None) -> str:
        self.s3.upload_fileobj(data, self.bucket_name, key, ExtraArgs={'Metadata': metadata or {}})
        return key

    async def get(self, key: str) -> BinaryIO:
        response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body']

    async def delete(self, key: str) -> bool:
        self.s3.delete_object(Bucket=self.bucket_name, Key=key)
        return True

    async def exists(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except:
            return False

    async def list(self, prefix: str = "") -> List[str]:
        response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        return [obj['Key'] for obj in response.get('Contents', [])]

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': key},
            ExpiresIn=expires_in
        )

class GoogleCloudStorage(StorageBackend):
    """Google Cloud Storage backend"""

    def __init__(self, bucket_name: str, project: str = None):
        self.client = gcs.Client(project=project)
        self.bucket = self.client.bucket(bucket_name)

    async def put(self, key: str, data: BinaryIO, metadata: Dict = None) -> str:
        blob = self.bucket.blob(key)
        blob.upload_from_file(data, metadata=metadata)
        return key

    async def get(self, key: str) -> BinaryIO:
        blob = self.bucket.blob(key)
        return blob.download_as_bytes()

    async def delete(self, key: str) -> bool:
        blob = self.bucket.blob(key)
        blob.delete()
        return True

    async def exists(self, key: str) -> bool:
        return self.bucket.blob(key).exists()

    async def list(self, prefix: str = "") -> List[str]:
        return [blob.name for blob in self.bucket.list_blobs(prefix=prefix)]

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        blob = self.bucket.blob(key)
        return blob.generate_signed_url(expiration=expires_in)

class AzureBlobStorage(StorageBackend):
    """Azure Blob Storage backend"""

    def __init__(self, connection_string: str, container_name: str):
        self.client = BlobServiceClient.from_connection_string(connection_string)
        self.container = self.client.get_container_client(container_name)

    async def put(self, key: str, data: BinaryIO, metadata: Dict = None) -> str:
        blob_client = self.container.get_blob_client(key)
        blob_client.upload_blob(data, metadata=metadata)
        return key

    async def get(self, key: str) -> BinaryIO:
        blob_client = self.container.get_blob_client(key)
        return blob_client.download_blob().readall()

    async def delete(self, key: str) -> bool:
        blob_client = self.container.get_blob_client(key)
        blob_client.delete_blob()
        return True

    async def exists(self, key: str) -> bool:
        blob_client = self.container.get_blob_client(key)
        return blob_client.exists()

    async def list(self, prefix: str = "") -> List[str]:
        return [blob.name for blob in self.container.list_blobs(name_starts_with=prefix)]

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        blob_client = self.container.get_blob_client(key)
        return blob_client.url

class StorageManager:
    """Manager for storage backends"""

    def __init__(self, config):
        self.config = config
        self._backends = {}
        self._default_backend = None

    def get_backend(self, name: str = None) -> StorageBackend:
        """Get storage backend by name"""
        if name is None:
            if self._default_backend is None:
                self._default_backend = self._create_backend(self.config.provider)
            return self._default_backend

        if name not in self._backends:
            self._backends[name] = self._create_backend(name)

        return self._backends[name]

    def _create_backend(self, provider: str) -> StorageBackend:
        """Create storage backend based on provider"""
        if provider == "local":
            return LocalStorage(self.config.local_directory)
        elif provider == "s3":
            return S3Storage(
                self.config.aws_bucket,
                self.config.aws_region,
                self.config.aws_access_key,
                self.config.aws_secret_key
            )
        elif provider == "gcs":
            return GoogleCloudStorage(
                self.config.gcp_bucket,
                self.config.gcp_project
            )
        elif provider == "azure":
            return AzureBlobStorage(
                f"DefaultEndpointsProtocol=https;AccountName={self.config.azure_account_name};AccountKey={self.config.azure_account_key}",
                self.config.azure_container
            )
        else:
            raise ValueError(f"Unsupported storage provider: {provider}")

# Global storage manager instance
storage_manager = None

def get_storage_manager(config=None) -> StorageManager:
    """Get global storage manager instance"""
    global storage_manager
    if storage_manager is None:
        from .config import AppConfig
        config = config or AppConfig()
        storage_manager = StorageManager(config.storage)
    return storage_manager




