from db import SessionLocal
import uuid
from datetime import datetime, timedelta, timezone
from logger import setup_logger
from models import Job, Transaction, CategoryStatus, JobStatus
from models import InsightRun, InsightRunStatus, AnomalyDecision
from services.llm import extract_transactions, categorize_transactions
from services.rules import rules_categorize
from services.pdf import extract_markdown
import tempfile
import os
from storage import s3, get_markdown_object_key
from config import settings
from cache import invalidate_job_summary_cache, invalidate_user_cache
from services.job_summary import recompute_job_summary
from services.insights import build_insights_payload
import json

logger = setup_logger("worker")


# -----------------------------
# Generate Transaction ID (UUID)
# -----------------------------
def generate_transaction_id():
    return str(uuid.uuid4())


def get_job_or_none(session, job_id: str, task_name: str):
    job = session.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        logger.warning(f"[{task_name}] Job not found, skipping. job_id={job_id}")
    return job


# -----------------------------
# Save Transactions
# -----------------------------
def save_transactions(session, job_id, transactions):
    for t in transactions:
        txn = Transaction(
            id=generate_transaction_id(),
            job_id=job_id,
            date=t["date"],
            description=t["description"],
            amount=t["amount"],
            category=None,
            category_status=CategoryStatus.pending,
        )
        session.add(txn)


# -----------------------------
# Update Categories
# -----------------------------
def update_categories(session, job_id, categorized):
    # STEP 1: mark successful ones — match by id (exact, unambiguous)
    for t in categorized:
        if not isinstance(t, dict):
            logger.warning(f"[DB] Skipping non-dict categorized entry: {type(t)} {t!r}")
            continue

        txn_id = t.get("id")
        category = t.get("category")

        if not txn_id or not category:
            logger.warning(f"[DB] Skipping categorized entry with missing fields: {t}")
            continue

        updated = (
            session.query(Transaction)
            .filter(
                Transaction.id == txn_id,
                Transaction.job_id == job_id,
                (
                    Transaction.category_status.in_(
                        [CategoryStatus.pending, CategoryStatus.failed]
                    )
                )
                | (Transaction.category_status.is_(None)),
            )
            .update(
                {
                    "category": category,
                    "category_status": CategoryStatus.done,
                    "updated_at": datetime.utcnow(),
                },
                synchronize_session=False,
            )
        )

        if updated == 0:
            logger.warning(f"[DB] No matching transaction found for id={txn_id!r}")

    # STEP 2: mark remaining as failed
    session.query(Transaction).filter(
        Transaction.job_id == job_id,
        (Transaction.category_status == CategoryStatus.pending)
        | (Transaction.category_status.is_(None)),
    ).update(
        {
            "category_status": CategoryStatus.failed,
            "updated_at": datetime.utcnow(),
        },
        synchronize_session=False,
    )


# -----------------------------
# Update Job Status
# -----------------------------
def update_job_status(session, job_id, status):
    session.query(Job).filter(Job.job_id == job_id).update(
        {"status": status, "updated_at": datetime.utcnow()},
        synchronize_session=False,
    )


# -----------------------------
# Main Worker Task
# -----------------------------
def process_pdf(object_key: str, job_id: str):
    logger.info(f"[Worker] Start processing {object_key}")
    session = SessionLocal()

    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, os.path.basename(object_key))

    try:
        if not get_job_or_none(session, job_id, "process_pdf"):
            return

        logger.info(f"[Worker] Downloading {object_key} to {file_path}")
        s3.download_file(settings.bucket_name, object_key, file_path)
        logger.info(f"[Worker] Downloaded {object_key} to {file_path}")

        # ✅ STEP 0: mark extracting
        if not get_job_or_none(session, job_id, "process_pdf"):
            return
        update_job_status(session, job_id, "extracting")
        session.commit()

        # STEP 1: PDF → Markdown
        markdown = extract_markdown(file_path)
        markdown_object_key = get_markdown_object_key(object_key)
        s3.put_object(
            Bucket=settings.bucket_name,
            Key=markdown_object_key,
            Body=markdown.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
        )
        logger.info(
            f"[Worker] Uploaded markdown debug artifact to {markdown_object_key}"
        )

        # STEP 2: Extract Transactions (LLM)
        transactions = extract_transactions(markdown)

        # ❌ only true failure
        if transactions is None:
            if not get_job_or_none(session, job_id, "process_pdf"):
                return
            update_job_status(session, job_id, "extract_failed")
            session.commit()
            job_row = session.query(Job).filter(Job.job_id == job_id).first()
            if job_row:
                invalidate_user_cache(job_row.user_id)
            return

        # STEP 3: Save Transactions
        if not get_job_or_none(session, job_id, "process_pdf"):
            return
        save_transactions(session, job_id, transactions)
        recompute_job_summary(session, job_id)

        # ✅ move to categorizing stage
        if not get_job_or_none(session, job_id, "process_pdf"):
            return
        update_job_status(session, job_id, "categorizing")
        session.commit()  # partial commit

        # Fetch saved rows so we have real DB IDs
        saved_rows = (
            session.query(Transaction).filter(Transaction.job_id == job_id).all()
        )

        transactions_for_categorization = [
            {
                "id": str(t.id),
                "date": str(t.date),
                "description": t.description,
                "amount": float(t.amount),  # Decimal → float for json.dumps()
            }
            for t in saved_rows
        ]

        # STEP 4a: Rules-based pre-categorization (fast, deterministic)
        rule_matched, llm_needed = rules_categorize(transactions_for_categorization)
        rule_results = [
            {"id": t["id"], "category": t["category"]} for t in rule_matched
        ]

        # STEP 4b: LLM categorization for remaining transactions
        categorized = categorize_transactions(llm_needed)

        # ❌ only true failure — but if rules caught some, partial results are still useful
        if categorized is None:
            if not rule_results:
                if not get_job_or_none(session, job_id, "process_pdf"):
                    return
                update_job_status(session, job_id, "categorize_failed")
                session.commit()
                job_row = session.query(Job).filter(Job.job_id == job_id).first()
                if job_row:
                    invalidate_user_cache(job_row.user_id)
                return
            logger.warning(
                "[Worker] LLM categorization failed; applying rule results only"
            )
            categorized = []

        # STEP 5: Update Categories (merge rule results + LLM results)
        update_categories(session, job_id, rule_results + categorized)
        recompute_job_summary(session, job_id)

        # STEP 6: Check if any failed remain
        remaining_failed = (
            session.query(Transaction)
            .filter(
                Transaction.job_id == job_id,
                Transaction.category_status == CategoryStatus.failed,
            )
            .first()
        )

        job_row = session.query(Job).filter(Job.job_id == job_id).first()
        if not job_row:
            logger.warning(
                f"[process_pdf] Job deleted before final status update. job_id={job_id}"
            )
            return
        if remaining_failed:
            update_job_status(session, job_id, "categorize_failed")
        else:
            update_job_status(session, job_id, "completed")

        session.commit()
        invalidate_job_summary_cache(job_id)

        if job_row:
            invalidate_user_cache(job_row.user_id)

        # STEP 7: Embed completed transactions into ChromaDB for RAG chatbot
        # Non-fatal — if Ollama's embed model isn't loaded, the job still
        # completes; users just can't query this job via /chat until re-embedded.
        try:
            from services.embeddings import upsert_transactions as _upsert
            embed_rows = (
                session.query(Transaction)
                .filter(Transaction.job_id == job_id)
                .all()
            )
            txn_dicts = [
                {
                    "id": t.id,
                    "job_id": job_id,
                    "date": str(t.date),
                    "description": t.description,
                    "amount": float(t.amount),
                    "category": t.category or "Uncategorized",
                }
                for t in embed_rows
            ]
            _upsert(txn_dicts, user_id=job_row.user_id)
            logger.info(
                f"[Worker] Embedded {len(txn_dicts)} transactions "
                f"for job {job_id}"
            )
        except Exception as embed_err:
            logger.warning(
                f"[Worker] Embedding step failed (non-fatal) for job {job_id}: "
                f"{embed_err}"
            )
        finally:
            recompute_job_summary(session, job_id, include_rag_brief=True)
            session.commit()
            invalidate_job_summary_cache(job_id)

        logger.info(f"[Worker] Completed {job_id}")

    except Exception as e:
        logger.error(f"[Worker] Failed: {e}")
        session.rollback()

        # fresh session for failure update
        fail_session = SessionLocal()
        try:
            if not get_job_or_none(fail_session, job_id, "process_pdf"):
                return
            update_job_status(fail_session, job_id, "failed")
            fail_session.commit()
            job_row = fail_session.query(Job).filter(Job.job_id == job_id).first()
            if job_row:
                invalidate_user_cache(job_row.user_id)
        finally:
            fail_session.close()

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass
        session.close()


# -----------------------------
# Retry Categorization
# -----------------------------
def retry_categorization(job_id: str):
    logger.info(f"[Worker] Retry categorization for {job_id}")
    session = SessionLocal()

    try:
        if not get_job_or_none(session, job_id, "retry_categorization"):
            return

        # STEP 1: fetch pending + failed
        rows = (
            session.query(Transaction)
            .filter(
                Transaction.job_id == job_id,
                Transaction.category_status.in_(
                    [CategoryStatus.pending, CategoryStatus.failed]
                ),
            )
            .all()
        )

        if not rows:
            if not get_job_or_none(session, job_id, "retry_categorization"):
                return
            update_job_status(session, job_id, "completed")
            session.commit()
            return

        # STEP 2: mark categorizing
        if not get_job_or_none(session, job_id, "retry_categorization"):
            return
        update_job_status(session, job_id, "categorizing")
        session.commit()

        transactions = [
            {
                "id": str(t.id),
                "date": str(t.date),
                "description": t.description,
                "amount": float(t.amount),  # Decimal → float for json.dumps()
            }
            for t in rows
        ]

        # STEP 3a: Rules-based pre-categorization
        rule_matched, llm_needed = rules_categorize(transactions)
        rule_results = [
            {"id": t["id"], "category": t["category"]} for t in rule_matched
        ]

        # STEP 3b: LLM for remaining
        categorized = categorize_transactions(llm_needed)

        if categorized is None:
            if not rule_results:
                if not get_job_or_none(session, job_id, "retry_categorization"):
                    return
                update_job_status(session, job_id, "categorize_failed")
                session.commit()
                return
            logger.warning(
                "[Worker] LLM categorization failed; applying rule results only"
            )
            categorized = []

        # STEP 4: Update categories (merge rule results + LLM results)
        update_categories(session, job_id, rule_results + categorized)
        recompute_job_summary(session, job_id)

        # STEP 5: check remaining failures
        remaining_failed = (
            session.query(Transaction)
            .filter(
                Transaction.job_id == job_id,
                Transaction.category_status == CategoryStatus.failed,
            )
            .first()
        )

        job_row = session.query(Job).filter(Job.job_id == job_id).first()
        if not job_row:
            logger.warning(
                f"[retry_categorization] Job deleted before final status update. "
                f"job_id={job_id}"
            )
            return
        if remaining_failed:
            update_job_status(session, job_id, "categorize_failed")
        else:
            update_job_status(session, job_id, "completed")

        session.commit()
        invalidate_job_summary_cache(job_id)

        if job_row:
            invalidate_user_cache(job_row.user_id)

        # Embed completed transactions into ChromaDB (non-fatal)
        try:
            from services.embeddings import upsert_transactions as _upsert
            embed_rows = (
                session.query(Transaction)
                .filter(Transaction.job_id == job_id)
                .all()
            )
            txn_dicts = [
                {
                    "id": t.id,
                    "job_id": job_id,
                    "date": str(t.date),
                    "description": t.description,
                    "amount": float(t.amount),
                    "category": t.category or "Uncategorized",
                }
                for t in embed_rows
            ]
            _upsert(txn_dicts, user_id=job_row.user_id)
            logger.info(
                f"[Worker] Retry: embedded {len(txn_dicts)} transactions "
                f"for job {job_id}"
            )
        except Exception as embed_err:
            logger.warning(
                f"[Worker] Retry embedding step failed (non-fatal) for job "
                f"{job_id}: {embed_err}"
            )
        finally:
            recompute_job_summary(session, job_id, include_rag_brief=True)
            session.commit()
            invalidate_job_summary_cache(job_id)

        logger.info(f"[Worker] Retry completed for {job_id}")

    except Exception as e:
        logger.error(f"[Worker] Retry failed for {job_id}: {e}")
        session.rollback()

        fail_session = SessionLocal()
        try:
            if not get_job_or_none(fail_session, job_id, "retry_categorization"):
                return
            update_job_status(fail_session, job_id, "failed")
            fail_session.commit()
            job_row = fail_session.query(Job).filter(Job.job_id == job_id).first()
            if job_row:
                invalidate_user_cache(job_row.user_id)
        finally:
            fail_session.close()

    finally:
        session.close()


def garbage_collect_s3_orphans(
    dry_run: bool = True,
    min_age_hours: int = 24,
) -> dict:
    """
    Delete S3 PDF/markdown artifacts that are no longer referenced by any Job.

    Safety:
    - Upload-vs-GC race: a worker can upload "<key>.pdf" (and markdown) before
      Job.s3_url is committed. If GC runs in that window, an orphaned-yet-soon-
      to-be-referenced key could be considered for deletion.
    - Current protection is operational: keep min_age_hours at its conservative
      default (24) so fresh uploads are not touched during this race window.
    - If maintainers change garbage_collect_s3_orphans defaults/usage, keep this
      invariant documented in backend/README.md and preserve equivalent safety.
    - dry_run defaults to True.
    - only keys older than min_age_hours are considered.
    - only *.pdf and *.pdf.md objects are eligible for deletion.
    """
    session = SessionLocal()
    try:
        referenced_keys: set[str] = set()
        s3_url_rows = (
            session.query(Job.s3_url)
            .filter(Job.s3_url.isnot(None))
            .yield_per(1000)
        )
        for (s3_url,) in s3_url_rows:
            if s3_url:
                referenced_keys.add(s3_url)
                referenced_keys.add(get_markdown_object_key(s3_url))
    finally:
        session.close()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(min_age_hours, 0))
    checked = 0
    candidates = 0
    deleted = 0
    skipped_not_old_enough = 0

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=settings.bucket_name)
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj.get("Key")
            if not key:
                continue

            checked += 1
            if key in referenced_keys:
                continue

            if not (key.endswith(".pdf") or key.endswith(".pdf.md")):
                continue

            last_modified = obj.get("LastModified")
            if last_modified and last_modified > cutoff:
                skipped_not_old_enough += 1
                continue

            candidates += 1
            if dry_run:
                logger.info(f"[S3-GC] Dry run candidate: {key}")
                continue

            try:
                s3.delete_object(Bucket=settings.bucket_name, Key=key)
                deleted += 1
                logger.info(f"[S3-GC] Deleted orphan object: {key}")
            except Exception as exc:
                logger.warning(f"[S3-GC] Failed deleting {key}: {exc}")

    result = {
        "dry_run": dry_run,
        "min_age_hours": min_age_hours,
        "checked": checked,
        "candidates": candidates,
        "deleted": deleted,
        "skipped_not_old_enough": skipped_not_old_enough,
    }
    logger.info(f"[S3-GC] Completed: {result}")
    return result


def run_user_insights(insight_run_id: str):
    session = SessionLocal()
    try:
        run = session.query(InsightRun).filter(InsightRun.id == insight_run_id).first()
        if not run:
            logger.warning(f"[Insights] Run not found: {insight_run_id}")
            return

        run.status = InsightRunStatus.running
        run.started_at = datetime.utcnow()
        session.commit()

        transactions = (
            session.query(Transaction)
            .join(Job, Job.job_id == Transaction.job_id)
            .filter(Job.user_id == run.user_id)
            .all()
        )
        dismissed = (
            session.query(AnomalyDecision.transaction_id)
            .filter(
                AnomalyDecision.user_id == run.user_id,
                AnomalyDecision.is_anomaly == 0,
            )
            .all()
        )
        dismissed_ids = {row.transaction_id for row in dismissed}

        result = build_insights_payload(transactions, dismissed_ids, run.user_id)
        run.result_json = json.dumps(result)
        run.status = InsightRunStatus.completed
        run.completed_at = datetime.utcnow()
        run.error = None
        session.commit()
    except Exception as exc:
        session.rollback()
        run = session.query(InsightRun).filter(InsightRun.id == insight_run_id).first()
        if run:
            run.status = InsightRunStatus.failed
            run.error = str(exc)
            run.completed_at = datetime.utcnow()
            session.commit()
        logger.error(f"[Insights] Failed run {insight_run_id}: {exc}", exc_info=True)
    finally:
        session.close()
