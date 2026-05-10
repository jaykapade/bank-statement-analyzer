from fastapi import APIRouter, Depends

from auth import get_current_user
from cache import invalidate_user_cache
from db import SessionLocal
from models import AnomalyDecision, InsightRun, Job, Transaction, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
def reset(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        jobs = session.query(Job).filter(Job.user_id == current_user.id).all()
        job_ids = [job.job_id for job in jobs]
        transaction_ids: list[str] = []

        if job_ids:
            transaction_ids = [
                txn_id
                for (txn_id,) in session.query(Transaction.id)
                .filter(Transaction.job_id.in_(job_ids))
                .all()
            ]
            if transaction_ids:
                session.query(AnomalyDecision).filter(
                    AnomalyDecision.transaction_id.in_(transaction_ids)
                ).delete(synchronize_session=False)
            session.query(Transaction).filter(Transaction.job_id.in_(job_ids)).delete(
                synchronize_session=False
            )

        session.query(AnomalyDecision).filter(
            AnomalyDecision.user_id == current_user.id
        ).delete(synchronize_session=False)
        session.query(InsightRun).filter(InsightRun.user_id == current_user.id).delete(
            synchronize_session=False
        )

        session.query(Job).filter(Job.user_id == current_user.id).delete(
            synchronize_session=False
        )
        session.commit()
        try:
            from services.embeddings import delete_user_transactions

            delete_user_transactions(str(current_user.id))
        except Exception:
            # Keep reset successful even if vector cleanup fails.
            pass
        invalidate_user_cache(str(current_user.id))
        return {"message": "Reset successful"}
    finally:
        session.close()
