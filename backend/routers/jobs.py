import io
import csv
import uuid
from decimal import Decimal, ROUND_HALF_UP

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from auth import get_current_user
from cache import invalidate_job_summary_cache, invalidate_user_cache
from config import settings
from db import SessionLocal
from logger import logger
from models import CategoryStatus, Job, JobStatus, Transaction, User
from redis import Redis
from rq import Queue
from services.job_summary import recompute_job_summary
from storage import get_markdown_object_key, s3
from tasks import retry_categorization

router = APIRouter(tags=["jobs"])

# RQ queue — shared within this process.
_redis_conn = Redis(host=settings.redis_host, port=settings.redis_port)
_queue = Queue(connection=_redis_conn)


class JobCreateRequest(BaseModel):
    filename: str | None = Field(default=None, max_length=255)


class JobUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str | None = Field(default=None, max_length=255)
    status: JobStatus | None = None


class TransactionCreateRequest(BaseModel):
    date: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=512)
    amount: Decimal
    category: str | None = Field(default=None, max_length=255)
    category_status: CategoryStatus = CategoryStatus.pending


class TransactionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, min_length=1, max_length=512)
    amount: Decimal | None = None
    category: str | None = Field(default=None, max_length=255)
    category_status: CategoryStatus | None = None


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


def get_owned_transaction_or_404(
    session,
    job_id: str,
    transaction_id: str,
    user_id: str,
) -> Transaction:
    transaction = (
        session.query(Transaction)
        .join(Job, Job.job_id == Transaction.job_id)
        .filter(
            Transaction.id == transaction_id,
            Transaction.job_id == job_id,
            Job.user_id == user_id,
        )
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


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


def serialize_amount(amount: Decimal | float | int | None) -> float | None:
    if amount is None:
        return None
    dec = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(dec)


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
            .order_by(Job.updated_at.desc(), Job.created_at.desc(), Job.job_id.desc())
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


@router.post("/jobs")
def create_job(
    payload: JobCreateRequest,
    current_user: User = Depends(get_current_user),
):
    session = SessionLocal()
    try:
        job = Job(
            job_id=str(uuid.uuid4()),
            user_id=current_user.id,
            filename=payload.filename,
            status=JobStatus.pending,
            s3_url=None,
        )
        session.add(job)
        session.commit()
        invalidate_user_cache(current_user.id)
        invalidate_job_summary_cache(job.job_id)
        return {
            "job_id": job.job_id,
            "status": job.status,
            "filename": job.filename,
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

        return {
            "job_id": job_id,
            "status": job.status,
            "total": job.summary_transaction_count,
            "done": job.summary_done_count,
            "failed": job.summary_failed_count,
            "pending": job.summary_pending_count,
        }
    finally:
        session.close()


@router.patch("/jobs/{job_id}")
def update_job(
    job_id: str,
    payload: JobUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    session = SessionLocal()
    try:
        job = get_owned_job_or_404(session, job_id, current_user.id)
        if "filename" in updates:
            job.filename = updates["filename"]
        if "status" in updates:
            job.status = updates["status"]

        session.commit()
        invalidate_user_cache(current_user.id)
        invalidate_job_summary_cache(job_id)
        return {
            "job_id": job.job_id,
            "status": job.status,
            "filename": job.filename,
        }
    finally:
        session.close()


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, current_user: User = Depends(get_current_user)):
    job_s3_url: str | None = None
    session = SessionLocal()
    try:
        job = get_owned_job_or_404(session, job_id, current_user.id)
        job_s3_url = job.s3_url

        deleted_transactions = (
            session.query(Transaction)
            .filter(Transaction.job_id == job_id)
            .delete(synchronize_session=False)
        )
        session.delete(job)
        session.commit()
        invalidate_user_cache(current_user.id)
        invalidate_job_summary_cache(job_id)
    finally:
        session.close()

    # Best effort cleanup for uploaded artifacts in object storage.
    if job_s3_url:
        keys_to_try = [job_s3_url, get_markdown_object_key(job_s3_url)]
        for object_key in keys_to_try:
            try:
                s3.delete_object(Bucket=settings.bucket_name, Key=object_key)
            except Exception as exc:
                logger.warning(
                    f"Failed to delete S3 object {object_key} for job {job_id}: {exc}"
                )

    # Best effort cleanup for ChromaDB vectors
    try:
        from services.embeddings import delete_job_transactions as _delete_vecs
        _delete_vecs(job_id)
    except Exception as exc:
        logger.warning(
            f"Failed to delete ChromaDB vectors for job {job_id}: {exc}"
        )

    return {
        "message": "Job deleted",
        "job_id": job_id,
        "deleted_transactions": deleted_transactions,
    }


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


def _get_transactions_page(
    job_id: str,
    current_user: User,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
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

        base_q = (
            session.query(Transaction)
            .filter(Transaction.job_id == job_id)
            .order_by(
                Transaction.created_at.asc(),
                Transaction.id.asc(),
            )
        )
        total = base_q.count()
        transactions = base_q.offset((page - 1) * limit).limit(limit).all()
        total_pages = max(1, (total + limit - 1) // limit)

        return {
            "job_id": job_id,
            "transactions": [
                {
                    "id": t.id,
                    "amount": serialize_amount(t.amount),
                    "category": t.category,
                    "category_status": t.category_status,
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


@router.get("/jobs/{job_id}/transactions")
def get_transactions(
    job_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    return _get_transactions_page(job_id, current_user, page, limit)


@router.get("/transactions/{job_id}")
def get_transactions_legacy(
    job_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    return _get_transactions_page(job_id, current_user, page, limit)


@router.post("/jobs/{job_id}/transactions")
def create_transaction(
    job_id: str,
    payload: TransactionCreateRequest,
    current_user: User = Depends(get_current_user),
):
    session = SessionLocal()
    try:
        get_owned_job_or_404(session, job_id, current_user.id)

        transaction = Transaction(
            id=str(uuid.uuid4()),
            job_id=job_id,
            date=payload.date,
            description=payload.description,
            amount=payload.amount,
            category=payload.category,
            category_status=payload.category_status,
        )
        session.add(transaction)
        recompute_job_summary(session, job_id)
        session.commit()
        invalidate_user_cache(current_user.id)
        invalidate_job_summary_cache(job_id)
        return {
            "id": transaction.id,
            "job_id": transaction.job_id,
            "amount": serialize_amount(transaction.amount),
            "category": transaction.category,
            "category_status": transaction.category_status,
            "description": transaction.description,
            "date": transaction.date,
        }
    finally:
        session.close()


@router.patch("/jobs/{job_id}/transactions/{transaction_id}")
def update_transaction(
    job_id: str,
    transaction_id: str,
    payload: TransactionUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    session = SessionLocal()
    try:
        transaction = get_owned_transaction_or_404(
            session, job_id, transaction_id, current_user.id
        )
        for key, value in updates.items():
            setattr(transaction, key, value)

        recompute_job_summary(session, job_id)
        session.commit()
        invalidate_user_cache(current_user.id)
        invalidate_job_summary_cache(job_id)
        return {
            "id": transaction.id,
            "job_id": transaction.job_id,
            "amount": serialize_amount(transaction.amount),
            "category": transaction.category,
            "category_status": transaction.category_status,
            "description": transaction.description,
            "date": transaction.date,
        }
    finally:
        session.close()


@router.delete("/jobs/{job_id}/transactions/{transaction_id}")
def delete_transaction(
    job_id: str,
    transaction_id: str,
    current_user: User = Depends(get_current_user),
):
    session = SessionLocal()
    try:
        transaction = get_owned_transaction_or_404(
            session, job_id, transaction_id, current_user.id
        )
        session.delete(transaction)
        recompute_job_summary(session, job_id)
        session.commit()
        invalidate_user_cache(current_user.id)
        invalidate_job_summary_cache(job_id)
        return {
            "message": "Transaction deleted",
            "id": transaction_id,
            "job_id": job_id,
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


@router.get("/jobs/{job_id}/export/transactions.csv")
def export_job_transactions_csv(
    job_id: str, current_user: User = Depends(get_current_user)
):
    session = SessionLocal()
    try:
        job = get_owned_job_or_404(session, job_id, current_user.id)
        rows = (
            session.query(Transaction)
            .filter(Transaction.job_id == job_id)
            .order_by(Transaction.date.asc(), Transaction.created_at.asc())
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "job_id",
                "filename",
                "date",
                "description",
                "amount",
                "category",
                "category_status",
                "transaction_id",
            ]
        )
        for t in rows:
            writer.writerow(
                [
                    job.job_id,
                    job.filename or "",
                    t.date or "",
                    t.description or "",
                    str(t.amount) if t.amount is not None else "",
                    t.category or "",
                    t.category_status or "",
                    t.id,
                ]
            )

        data = output.getvalue().encode("utf-8")
        headers = {
            "Content-Disposition": f'attachment; filename="transactions-{job_id}.csv"',
            "Cache-Control": "no-store",
        }
        return Response(content=data, media_type="text/csv; charset=utf-8", headers=headers)
    finally:
        session.close()


@router.get("/jobs/export/transactions.csv")
def export_all_transactions_csv(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        rows = (
            session.query(Transaction, Job)
            .join(Job, Job.job_id == Transaction.job_id)
            .filter(Job.user_id == current_user.id)
            .order_by(Job.created_at.desc(), Transaction.date.asc(), Transaction.created_at.asc())
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "job_id",
                "filename",
                "date",
                "description",
                "amount",
                "category",
                "category_status",
                "transaction_id",
            ]
        )
        for txn, job in rows:
            writer.writerow(
                [
                    job.job_id,
                    job.filename or "",
                    txn.date or "",
                    txn.description or "",
                    str(txn.amount) if txn.amount is not None else "",
                    txn.category or "",
                    txn.category_status or "",
                    txn.id,
                ]
            )

        data = output.getvalue().encode("utf-8")
        headers = {
            "Content-Disposition": 'attachment; filename="transactions-all-jobs.csv"',
            "Cache-Control": "no-store",
        }
        return Response(content=data, media_type="text/csv; charset=utf-8", headers=headers)
    finally:
        session.close()

