import boto3
from botocore.client import Config
import os

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = "bank-statements"

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
)


def init_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except Exception:
        s3.create_bucket(Bucket=BUCKET_NAME)


def get_markdown_object_key(pdf_object_key: str) -> str:
    return f"{pdf_object_key}.md"
