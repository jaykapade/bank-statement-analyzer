from fastapi import APIRouter, Depends

from auth import get_current_user
from cache import invalidate_user_cache
from db import SessionLocal
from models import Job, Transaction, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
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
        invalidate_user_cache(str(current_user.id))
        return {"message": "Reset successful"}
    finally:
        session.close()
