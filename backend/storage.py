import boto3
from botocore.client import Config

from config import settings

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{settings.minio_endpoint}",
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key,
    config=Config(signature_version="s3v4"),
)


def init_bucket():
    try:
        s3.head_bucket(Bucket=settings.bucket_name)
    except Exception:
        s3.create_bucket(Bucket=settings.bucket_name)


def get_markdown_object_key(pdf_object_key: str) -> str:
    return f"{pdf_object_key}.md"
