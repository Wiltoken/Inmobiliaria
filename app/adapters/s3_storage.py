"""S3/MinIO storage adapter for property photos and other file uploads."""

from __future__ import annotations

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import settings


def get_s3_client():
    """Return an async-capable S3 client."""
    return boto3.client(
        "s3",
        endpoint_url=getattr(settings, "s3_endpoint_url", None),
        aws_access_key_id=getattr(settings, "s3_access_key", None),
        aws_secret_access_key=getattr(settings, "s3_secret_key", None),
        region_name=getattr(settings, "s3_region", "us-east-1"),
        config=BotoConfig(signature_version="s3v4"),
    )


class S3StorageAdapter:
    """S3/MinIO storage operations for property photos."""

    def __init__(self, bucket: str = "inmobiliaria-photos"):
        self.bucket = bucket
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_s3_client()
        return self._client

    def upload_file(self, file_content: bytes, key: str) -> str:
        """Upload a file to S3 and return the URL.

        Args:
            file_content: Raw bytes of the file
            key: S3 object key (e.g., 'properties/uuid/photo_001.jpg')

        Returns:
            The public URL of the uploaded file
        """
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_content,
                ContentType=self._guess_content_type(key),
            )
            return self._build_url(key)
        except ClientError as exc:
            raise RuntimeError(f"Failed to upload file to S3: {exc}") from exc

    def delete_file(self, key: str) -> None:
        """Delete a file from S3.

        Args:
            key: S3 object key to delete
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            raise RuntimeError(f"Failed to delete file from S3: {exc}") from exc

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for temporary access.

        Args:
            key: S3 object key
            expiration: URL validity in seconds (default 1 hour)

        Returns:
            Presigned URL string
        """
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration,
            )
        except ClientError as exc:
            raise RuntimeError(f"Failed to generate presigned URL: {exc}") from exc

    def _build_url(self, key: str) -> str:
        """Build public URL for an S3 object."""
        endpoint = getattr(settings, "s3_endpoint_url", None)
        if endpoint:
            return f"{endpoint}/{self.bucket}/{key}"
        # Fall back to standard S3 URL
        region = getattr(settings, "s3_region", "us-east-1")
        return f"https://{self.bucket}.s3.{region}.amazonaws.com/{key}"

    def _guess_content_type(self, key: str) -> str:
        """Guess content type from file extension."""
        ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
        mapping = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "heic": "image/heic",
            "heif": "image/heif",
        }
        return mapping.get(ext, "application/octet-stream")


# Module-level singleton
_s3_adapter: S3StorageAdapter | None = None


def get_s3_adapter() -> S3StorageAdapter:
    """Return the singleton S3 adapter instance."""
    global _s3_adapter
    if _s3_adapter is None:
        bucket = getattr(settings, "s3_bucket", "inmobiliaria-photos")
        _s3_adapter = S3StorageAdapter(bucket=bucket)
    return _s3_adapter
