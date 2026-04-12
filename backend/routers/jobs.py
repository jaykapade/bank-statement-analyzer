import io

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from auth import get_current_user
from config import settings
from db import SessionLocal
from logger import logger
from models import CategoryStatus, Job, JobStatus, Transaction, User
from redis import Redis
from rq import Queue
from storage import get_markdown_object_key, s3
from tasks import retry_categorization

router = APIRouter(tags=["jobs"])

# RQ queue — shared within this process.
_redis_conn = Redis(host=settings.redis_host, port=settings.redis_port)
_queue = Queue(connection=_redis_conn)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def get_owned_job_or_404(session, job_id: str, user_id: str) -> Job:
    job = (
        session.query(Job).filter(Job.job_id == job_id, Job.user_id == user_id).first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def read_s3_bytes_or_404(object_key: str) -> bytes:
    try:
        response = s3.get_object(Bucket=settings.bucket_name, Key=object_key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"NoSuchKey", "404"}:
            raise HTTPException(status_code=404, detail="Preview not available")
        logger.error(f"Failed to read S3 object {object_key}: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail="Unable to load preview")

    body = response["Body"]
    try:
        return body.read()
    finally:
        body.close()


def ensure_markdown_bytes(job: Job) -> bytes:
    """
    Read the pre-generated markdown artifact from S3.

    NOTE: We intentionally do NOT fall back to running Docling here.
    The worker is responsible for generating and uploading the markdown artifact.
    Running Docling inside the FastAPI process in parallel with the worker
    causes two concurrent Docling instances → memory exhaustion → segfault.
    If the artifact isn't ready yet, return 404 and let the client retry.
    """
    if not job.s3_url:
        raise HTTPException(status_code=404, detail="Preview not available")

    markdown_key = get_markdown_object_key(job.s3_url)
    return read_s3_bytes_or_404(markdown_key)


# ---------------------------------------------------------------------------
# Job list + detail
# ---------------------------------------------------------------------------


@router.get("/jobs")
def get_jobs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    session = SessionLocal()
    try:
        base_q = (
            session.query(Job)
            .filter(Job.user_id == current_user.id)
            .order_by(Job.job_id.desc())
        )
        total = base_q.count()
        jobs = base_q.offset((page - 1) * limit).limit(limit).all()
        total_pages = max(1, (total + limit - 1) // limit)
        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "filename": job.filename,
                }
                for job in jobs
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
    finally:
        session.close()


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        job = (
            session.query(Job)
            .filter(Job.job_id == job_id, Job.user_id == current_user.id)
            .first()
        )

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


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


@router.get("/transactions/{job_id}")
def get_transactions(
    job_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    session = SessionLocal()
    try:
        job = (
            session.query(Job)
            .filter(Job.job_id == job_id, Job.user_id == current_user.id)
            .first()
        )

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        base_q = session.query(Transaction).filter(Transaction.job_id == job_id)
        total = base_q.count()

        if total == 0:
            raise HTTPException(status_code=404, detail="Transactions not found")

        transactions = base_q.offset((page - 1) * limit).limit(limit).all()
        total_pages = max(1, (total + limit - 1) // limit)

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
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Categorization retry
# ---------------------------------------------------------------------------


@router.get("/categorize/retry/{job_id}")
def retry_job(job_id: str, current_user: User = Depends(get_current_user)):
    session = SessionLocal()

    try:
        job = (
            session.query(Job)
            .filter(Job.job_id == job_id, Job.user_id == current_user.id)
            .first()
        )

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status == JobStatus.completed:
            raise HTTPException(status_code=400, detail="Job already completed")

        retryable = {JobStatus.categorize_failed, JobStatus.failed}
        if job.status not in retryable:
            raise HTTPException(
                status_code=400, detail=f"Job is not retryable (status: {job.status})"
            )

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
        _queue.enqueue(
            retry_categorization, job_id, job_timeout=settings.job_timeout_seconds
        )
    except Exception as e:
        logger.error(f"Redis/RQ enqueue failed for retry {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, detail="Background processing service unavailable"
        )

    return {"message": "Retry started", "job_id": job_id}


# ---------------------------------------------------------------------------
# Job assets (PDF / Markdown previews)
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/assets/pdf")
def preview_job_pdf(job_id: str, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        job = get_owned_job_or_404(session, job_id, current_user.id)
        if not job.s3_url:
            raise HTTPException(status_code=404, detail="Preview not available")

        pdf_bytes = read_s3_bytes_or_404(job.s3_url)
        filename = job.filename or f"{job_id}.pdf"
        headers = {
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers=headers,
        )
    finally:
        session.close()


@router.get("/jobs/{job_id}/assets/markdown")
def preview_job_markdown(job_id: str, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        job = get_owned_job_or_404(session, job_id, current_user.id)
        markdown_bytes = ensure_markdown_bytes(job)
        headers = {
            "Content-Disposition": f'inline; filename="{job_id}.md"',
            "Cache-Control": "no-store",
        }
        return Response(
            content=markdown_bytes,
            media_type="text/markdown; charset=utf-8",
            headers=headers,
        )
    finally:
        session.close()
