"""
MinIO / S3-compatible object storage service using boto3.

QR codes are stored under the public qr/ prefix and served via direct URLs.
Certificates and other private files use presigned URLs via _s3_public so
the signature matches what the browser sends (signed against localhost:9000,
not the internal minio:9000).
"""
import logging

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# boto3 clients
# _s3        — internal endpoint (minio:9000)  — used for uploads / bucket ops
# _s3_public — public endpoint  (localhost:9000) — used for presigned URLs
#              so the HMAC signature matches what the browser sends
# ---------------------------------------------------------------------------

def _make_client(endpoint: str) -> boto3.client:
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if settings.MINIO_SECURE else 'http'}://{endpoint}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


_s3 = _make_client(settings.MINIO_ENDPOINT)

_public_endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
_s3_public = (
    _make_client(_public_endpoint)
    if _public_endpoint != settings.MINIO_ENDPOINT
    else _s3
)

BUCKET = settings.MINIO_BUCKET_NAME


def ensure_bucket_exists() -> None:
    """Create the bucket if it does not already exist. Called on app startup."""
    try:
        _s3.head_bucket(Bucket=BUCKET)
        logger.info("MinIO bucket '%s' already exists.", BUCKET)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("404", "NoSuchBucket"):
            _s3.create_bucket(Bucket=BUCKET)
            logger.info("Created MinIO bucket '%s'.", BUCKET)
        else:
            logger.error("Error checking MinIO bucket: %s", e)
            raise


def upload_file(file_bytes: bytes, object_name: str, content_type: str) -> str:
    """Upload bytes to MinIO. Returns object_name."""
    import io
    _s3.upload_fileobj(
        io.BytesIO(file_bytes),
        BUCKET,
        object_name,
        ExtraArgs={"ContentType": content_type},
    )
    logger.info("Uploaded '%s' to bucket '%s'.", object_name, BUCKET)
    return object_name


def get_public_url(object_name: str) -> str:
    """
    Return a direct public URL for objects in a public-read prefix (e.g. qr/).
    No signature — MinIO serves these without auth.
    Uses MINIO_PUBLIC_ENDPOINT so the URL is reachable from the browser.
    """
    scheme = "https" if settings.MINIO_SECURE else "http"
    endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
    return f"{scheme}://{endpoint}/{BUCKET}/{object_name}"


def get_presigned_url(object_name: str, expires_in_seconds: int = 3600) -> str:
    """
    Generate a presigned GET URL for private objects (e.g. certificates).
    Signed against _s3_public so the URL works directly in the browser.
    """
    return _s3_public.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": object_name},
        ExpiresIn=expires_in_seconds,
    )
