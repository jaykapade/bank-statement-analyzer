from db import SessionLocal
import uuid
from datetime import datetime
from logger import setup_logger
from models import Job, Transaction, CategoryStatus, JobStatus
from services.llm import extract_transactions, categorize_transactions
from services.rules import rules_categorize
from services.pdf import extract_markdown
import tempfile
import os
from storage import s3, get_markdown_object_key
from config import settings
from cache import invalidate_user_cache

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
                Transaction.category_status.in_(
                    [CategoryStatus.pending, CategoryStatus.failed]
                ),
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
        Transaction.category_status == CategoryStatus.pending,
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
                "amount": t.amount,
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

        if job_row:
            invalidate_user_cache(job_row.user_id)
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
                "amount": t.amount,
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

        if job_row:
            invalidate_user_cache(job_row.user_id)
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
