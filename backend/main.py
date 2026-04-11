from contextlib import asynccontextmanager
from pydantic import BaseModel
from models import CategoryStatus
from fastapi.responses import JSONResponse, StreamingResponse
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

from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
import uuid
import io
from config import settings
from storage import s3, init_bucket
from storage import get_markdown_object_key

from redis import Redis
from rq import Queue

from auth import (
    apply_session_cookie,
    clear_session_cookie,
    create_session,
    destroy_session,
    get_current_user,
    get_db,
    hash_password,
    normalize_email,
    serialize_user,
    utcnow,
    verify_password,
)
from db import SessionLocal
from models import Job, Transaction, JobStatus, User
from tasks import process_pdf, retry_categorization
from logger import logger
from botocore.exceptions import ClientError


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


class AuthRequest(BaseModel):
    email: str
    password: str


def get_owned_job_or_404(session, job_id: str, user_id: str):
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


def validate_password(password: str):
    if len(password) < settings.password_min_length:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {settings.password_min_length} characters long",
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Redis connection
redis_conn = Redis(host=settings.redis_host, port=settings.redis_port)

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


@app.post("/auth/register", status_code=201)
def register(payload: AuthRequest, response: Response, db=Depends(get_db)):
    email = normalize_email(payload.email)
    validate_password(payload.password)

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(payload.password),
        created_at=utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_session(db, user)
    apply_session_cookie(response, token)

    return {"user": serialize_user(user)}


@app.post("/auth/login")
def login(payload: AuthRequest, response: Response, db=Depends(get_db)):
    email = normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_session(db, user)
    apply_session_cookie(response, token)

    return {"user": serialize_user(user)}


@app.post("/auth/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    destroy_session(db, request.cookies.get(settings.session_cookie_name))
    clear_session_cookie(response)
    return {"message": "Logged out"}


@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {"user": serialize_user(current_user)}


@app.post("/upload")
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

    # Create the job record so it's immediately visible to /jobs/{job_id}
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
        # try sending job to Redis
        queue.enqueue(
            process_pdf, object_key, job_id, job_timeout=settings.job_timeout_seconds
        )

    except Exception as e:
        logger.error(f"Redis/RQ enqueue failed for job {job_id}: {e}", exc_info=True)

        # return proper API error (like throwing in Next.js)
        raise HTTPException(
            status_code=503, detail="Background processing service unavailable"
        )

    return {"message": "Processing started", "job_id": job_id}


@app.get("/jobs")
def get_jobs(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        jobs = (
            session.query(Job)
            .filter(Job.user_id == current_user.id)
            .order_by(Job.job_id.desc())
            .all()
        )
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


@app.get("/transactions/{job_id}")
def get_transactions(job_id: str, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        job = (
            session.query(Job)
            .filter(Job.job_id == job_id, Job.user_id == current_user.id)
            .first()
        )

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

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
        queue.enqueue(
            retry_categorization, job_id, job_timeout=settings.job_timeout_seconds
        )
    except Exception as e:
        logger.error(f"Redis/RQ enqueue failed for retry {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, detail="Background processing service unavailable"
        )

    return {"message": "Retry started", "job_id": job_id}


@app.post("/reset")
def reset(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        jobs = session.query(Job).filter(Job.user_id == current_user.id).all()
        job_ids = [job.job_id for job in jobs]

        if job_ids:
            session.query(Transaction).filter(Transaction.job_id.in_(job_ids)).delete(
                synchronize_session=False
            )

        session.query(Job).filter(Job.user_id == current_user.id).delete(
            synchronize_session=False
        )
        session.commit()
        return {"message": "Reset successful"}
    finally:
        session.close()


@app.get("/jobs/{job_id}/assets/pdf")
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


@app.get("/jobs/{job_id}/assets/markdown")
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
