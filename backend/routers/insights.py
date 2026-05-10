import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from redis import Redis
from rq import Queue

from auth import get_current_user
from cache import invalidate_job_summary_cache, invalidate_user_cache
from config import settings
from db import SessionLocal
from models import AnomalyDecision, InsightRun, InsightRunStatus, Job, Transaction, User
from services.job_summary import recompute_job_summary
from tasks import run_user_insights

router = APIRouter(prefix="/insights", tags=["insights"])
_redis_conn = Redis(host=settings.redis_host, port=settings.redis_port)
_queue = Queue(connection=_redis_conn)


class DismissAnomalyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = Field(default=None, max_length=300)


@router.post("/run")
def start_insights(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    run_id = str(uuid.uuid4())
    run_status = InsightRunStatus.pending
    try:
        run = InsightRun(
            id=run_id,
            user_id=current_user.id,
            status=run_status,
        )
        session.add(run)
        session.commit()
    finally:
        session.close()

    try:
        _queue.enqueue(
            run_user_insights,
            run_id,
            job_timeout=settings.job_timeout_seconds,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to queue insights: {exc}")

    return {"run_id": run_id, "status": run_status}


@router.get("/runs/latest")
def get_latest_insight_run(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        run = (
            session.query(InsightRun)
            .filter(InsightRun.user_id == current_user.id)
            .order_by(InsightRun.created_at.desc())
            .first()
        )
        if not run:
            return {"run": None}
        payload = json.loads(run.result_json) if run.result_json else None
        return {
            "run": {
                "id": run.id,
                "status": run.status,
                "error": run.error,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": (
                    run.completed_at.isoformat() if run.completed_at else None
                ),
                "result": payload,
            }
        }
    finally:
        session.close()


@router.post("/anomalies/{transaction_id}/dismiss")
def dismiss_anomaly(
    transaction_id: str,
    payload: DismissAnomalyRequest,
    current_user: User = Depends(get_current_user),
):
    session = SessionLocal()
    try:
        txn = (
            session.query(Transaction)
            .join(Job, Job.job_id == Transaction.job_id)
            .filter(Transaction.id == transaction_id, Job.user_id == current_user.id)
            .first()
        )
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")

        decision = (
            session.query(AnomalyDecision)
            .filter(
                AnomalyDecision.user_id == current_user.id,
                AnomalyDecision.transaction_id == transaction_id,
            )
            .first()
        )
        if not decision:
            decision = AnomalyDecision(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                transaction_id=transaction_id,
                is_anomaly=0,
                reason=payload.reason,
            )
            session.add(decision)
        else:
            decision.is_anomaly = 0
            decision.reason = payload.reason
        session.commit()
        return {"message": "Anomaly dismissed", "transaction_id": transaction_id}
    finally:
        session.close()


@router.delete("/anomalies/{transaction_id}")
def delete_anomaly_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
):
    new_run_id: str | None = None
    session = SessionLocal()
    try:
        row = (
            session.query(Transaction, Job)
            .join(Job, Job.job_id == Transaction.job_id)
            .filter(Transaction.id == transaction_id, Job.user_id == current_user.id)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found")

        txn, job = row
        job_id = txn.job_id

        session.query(AnomalyDecision).filter(
            AnomalyDecision.user_id == current_user.id,
            AnomalyDecision.transaction_id == transaction_id,
        ).delete(synchronize_session=False)
        session.delete(txn)
        recompute_job_summary(session, job_id)
        session.commit()
        invalidate_user_cache(current_user.id)
        invalidate_job_summary_cache(job_id)
    finally:
        session.close()

    try:
        from services.embeddings import delete_transaction_embeddings

        delete_transaction_embeddings([transaction_id])
    except Exception:
        # Non-fatal cleanup
        pass

    return {
        "message": "Anomaly transaction deleted",
        "transaction_id": transaction_id,
        "job_id": job_id,
        "insights_run_id": new_run_id,
    }
