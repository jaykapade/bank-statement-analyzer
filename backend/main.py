from contextlib import asynccontextmanager
from models import CategoryStatus
from fastapi.responses import JSONResponse
import sys
import multiprocessing
import multiprocessing.context

# RQ's scheduler.py calls get_context('fork') at import time.
# Windows doesn't support 'fork' so we intercept the call and redirect to 'spawn'.
if sys.platform == "win32":
    _original_get_context = multiprocessing.context.BaseContext.get_context

    def _patched_get_context(self, method=None):
        if method == "fork":
            method = "spawn"
        return _original_get_context(self, method)

    multiprocessing.context.BaseContext.get_context = _patched_get_context

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
import os
import uuid
from storage import s3, BUCKET_NAME, init_bucket

from redis import Redis
from rq import Queue

from db import SessionLocal
from models import Job, Transaction, JobStatus
from tasks import process_pdf, retry_categorization
from logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_bucket()
        logger.info("S3 bucket initialized")
    except Exception as e:
        logger.error(f"Failed to initialize S3 bucket: {e}", exc_info=True)
        raise  # fail fast — don't start the app without storage
    yield


app = FastAPI(lifespan=lifespan)


# Redis connection
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_conn = Redis(host=redis_host, port=6379)

queue = Queue(connection=redis_conn)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Service temporarily unavailable, try later"},
    )


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/healthy")
def healthy():
    return {"status": "healthy"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    object_key = f"{job_id}/{file.filename}"

    logger.info(f"Uploading {file.filename} to S3")
    file_bytes = await file.read()
    s3.put_object(Bucket=BUCKET_NAME, Key=object_key, Body=file_bytes)
    logger.info(f"Uploaded {file.filename} to S3: {object_key}")

    # Create the job record so it's immediately visible to /jobs/{job_id}
    session = SessionLocal()
    try:
        session.add(
            Job(
                job_id=job_id,
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
        # try sending job to Redis
        queue.enqueue(process_pdf, object_key, job_id)

    except Exception as e:
        logger.error(f"Redis/RQ enqueue failed for job {job_id}: {e}", exc_info=True)

        # return proper API error (like throwing in Next.js)
        raise HTTPException(
            status_code=503, detail="Background processing service unavailable"
        )

    return {"message": "Processing started", "job_id": job_id}


@app.get("/jobs")
def get_jobs():
    session = SessionLocal()
    try:
        jobs = session.query(Job).all()
        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "filename": job.filename,
                }
                for job in jobs
            ],
        }
    finally:
        session.close()


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    session = SessionLocal()

    try:
        job = session.query(Job).filter(Job.job_id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        total = session.query(Transaction).filter(Transaction.job_id == job_id).count()

        done = (
            session.query(Transaction)
            .filter(
                Transaction.job_id == job_id,
                Transaction.category_status == CategoryStatus.done,
            )
            .count()
        )

        failed = (
            session.query(Transaction)
            .filter(
                Transaction.job_id == job_id,
                Transaction.category_status == CategoryStatus.failed,
            )
            .count()
        )

        pending = (
            session.query(Transaction)
            .filter(
                Transaction.job_id == job_id,
                Transaction.category_status == CategoryStatus.pending,
            )
            .count()
        )

        return {
            "job_id": job_id,
            "status": job.status,
            "total": total,
            "done": done,
            "failed": failed,
            "pending": pending,
        }

    finally:
        session.close()


@app.get("/transactions/{job_id}")
def get_transactions(job_id: str):
    session = SessionLocal()
    try:
        transactions = (
            session.query(Transaction).filter(Transaction.job_id == job_id).all()
        )

        if not transactions:
            raise HTTPException(status_code=404, detail="Transactions not found")

        return {
            "job_id": job_id,
            "transactions": [
                {
                    "amount": t.amount,
                    "category": t.category,
                    "description": t.description,
                    "date": t.date,
                }
                for t in transactions
            ],
        }
    finally:
        session.close()


@app.get("/categorize/retry/{job_id}")
def retry_job(job_id: str):
    session = SessionLocal()

    try:
        job = session.query(Job).filter(Job.job_id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status == JobStatus.completed:
            raise HTTPException(status_code=400, detail="Job already completed")

        # Only retryable states
        retryable = {JobStatus.categorize_failed, JobStatus.failed}
        if job.status not in retryable:
            raise HTTPException(
                status_code=400, detail=f"Job is not retryable (status: {job.status})"
            )

        # ✅ Check if any work exists
        has_work = (
            session.query(Transaction)
            .filter(
                Transaction.job_id == job_id,
                Transaction.category_status.in_(
                    [CategoryStatus.pending, CategoryStatus.failed]
                ),
            )
            .first()
        )

        if not has_work:
            raise HTTPException(status_code=400, detail="No transactions to retry")

    finally:
        session.close()

    try:
        queue.enqueue(retry_categorization, job_id)
    except Exception as e:
        logger.error(f"Redis/RQ enqueue failed for retry {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, detail="Background processing service unavailable"
        )

    return {"message": "Retry started", "job_id": job_id}


@app.post("/reset")
def reset():
    session = SessionLocal()
    try:
        session.query(Transaction).delete()
        session.query(Job).delete()
        session.commit()
        return {"message": "Reset successful"}
    finally:
        session.close()
