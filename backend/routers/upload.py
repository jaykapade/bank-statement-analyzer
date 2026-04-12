import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import get_current_user
from config import settings
from db import SessionLocal
from logger import logger
from models import Job, JobStatus, User
from redis import Redis
from rq import Queue
from storage import s3
from tasks import process_pdf

router = APIRouter(tags=["upload"])

_redis_conn = Redis(host=settings.redis_host, port=settings.redis_port)
_queue = Queue(connection=_redis_conn)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    job_id = str(uuid.uuid4())
    object_key = f"{job_id}/{file.filename}"

    logger.info(f"Uploading {file.filename} to S3")
    file_bytes = await file.read()
    s3.put_object(Bucket=settings.bucket_name, Key=object_key, Body=file_bytes)
    logger.info(f"Uploaded {file.filename} to S3: {object_key}")

    session = SessionLocal()
    try:
        session.add(
            Job(
                job_id=job_id,
                user_id=current_user.id,
                status=JobStatus.pending,
                filename=file.filename,
                s3_url=object_key,
            )
        )
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create job record for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create job")
    finally:
        session.close()

    try:
        _queue.enqueue(
            process_pdf, object_key, job_id, job_timeout=settings.job_timeout_seconds
        )
    except Exception as e:
        logger.error(f"Redis/RQ enqueue failed for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, detail="Background processing service unavailable"
        )

    return {"message": "Processing started", "job_id": job_id}
