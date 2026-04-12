"""
Analysis endpoints for the dashboard.

All endpoints are user-scoped (authenticated), aggregate across every job
belonging to the current user, and honour optional date-range filters.

Caching
-------
- Results are cached in Redis under a per-user key for TTL_ANALYSIS seconds
  (default 5 min, configurable via CACHE_TTL_ANALYSIS env var).
- The cache is invalidated by the worker whenever a job reaches a terminal
  state, so the frontend always gets fresh data after processing finishes.

Date filtering
--------------
All endpoints accept optional ?from=YYYY-MM-DD and ?to=YYYY-MM-DD query
parameters. Dates are matched against the Transaction.date column (which
stores ISO-8601 strings). No date filter → all-time data.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user, get_db
from cache import TTL_ANALYSIS, TTL_JOB_SUMMARY, get_cached, set_cached
from models import CategoryStatus, Job, JobStatus, Transaction, User

router = APIRouter(prefix="/analysis", tags=["analysis"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _date_filter(query, from_date: date | None, to_date: date | None):
    """Apply date range filter to a SQLAlchemy query on Transaction."""
    if from_date:
        query = query.filter(Transaction.date >= from_date.isoformat())
    if to_date:
        query = query.filter(Transaction.date <= to_date.isoformat())
    return query


def _build_date_range_suffix(from_date: date | None, to_date: date | None) -> str:
    f = from_date.isoformat() if from_date else "all"
    t = to_date.isoformat() if to_date else "all"
    return f"{f}:{t}"


def _job_ids_for_user(db: Session, user_id: str) -> list[str]:
    rows = db.query(Job.job_id).filter(Job.user_id == user_id).all()
    return [r.job_id for r in rows]


# ---------------------------------------------------------------------------
# GET /analysis/summary
# ---------------------------------------------------------------------------


@router.get("/summary")
def analysis_summary(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dr = _build_date_range_suffix(from_date, to_date)
    cache_key = f"analysis:summary:{current_user.id}:{dr}"

    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    # --- Job stats (not date-filtered — job counts span all time) ---
    job_ids = _job_ids_for_user(db, current_user.id)

    job_totals = (
        db.query(Job.status, func.count(Job.job_id).label("cnt"))
        .filter(Job.user_id == current_user.id)
        .group_by(Job.status)
        .all()
    )
    job_counts: dict[str, int] = {r.status: r.cnt for r in job_totals}

    jobs_summary = {
        "total": sum(job_counts.values()),
        "completed": job_counts.get(JobStatus.completed, 0),
        "pending": (
            job_counts.get(JobStatus.pending, 0)
            + job_counts.get(JobStatus.extracting, 0)
            + job_counts.get(JobStatus.extracted, 0)
            + job_counts.get(JobStatus.categorizing, 0)
        ),
        "failed": (
            job_counts.get(JobStatus.failed, 0)
            + job_counts.get(JobStatus.extract_failed, 0)
            + job_counts.get(JobStatus.categorize_failed, 0)
        ),
    }

    if not job_ids:
        result = {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "net_flow": 0.0,
            "transaction_count": 0,
            "uncategorized_count": 0,
            "date_range": {"from": dr.split(":")[0], "to": dr.split(":")[1]},
            "jobs": jobs_summary,
        }
        set_cached(cache_key, result, ttl=TTL_ANALYSIS, user_id=current_user.id)
        return result

    # --- Transaction aggregates (date-filtered) ---
    base_q = db.query(Transaction).filter(Transaction.job_id.in_(job_ids))
    base_q = _date_filter(base_q, from_date, to_date)

    transactions = base_q.all()

    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
    uncategorized = sum(1 for t in transactions if not t.category)

    result = {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_flow": round(total_income - total_expenses, 2),
        "transaction_count": len(transactions),
        "uncategorized_count": uncategorized,
        "date_range": {
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
        },
        "jobs": jobs_summary,
    }

    set_cached(cache_key, result, ttl=TTL_ANALYSIS, user_id=current_user.id)
    return result


# ---------------------------------------------------------------------------
# GET /analysis/spending-trend
# ---------------------------------------------------------------------------


@router.get("/spending-trend")
def analysis_spending_trend(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    group_by: str = Query(default="day", pattern="^(day|week|month)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dr = _build_date_range_suffix(from_date, to_date)
    cache_key = f"analysis:trend:{current_user.id}:{dr}:{group_by}"

    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    job_ids = _job_ids_for_user(db, current_user.id)
    if not job_ids:
        result = {"trend": [], "group_by": group_by}
        set_cached(cache_key, result, ttl=TTL_ANALYSIS, user_id=current_user.id)
        return result

    base_q = db.query(Transaction).filter(Transaction.job_id.in_(job_ids))
    base_q = _date_filter(base_q, from_date, to_date)
    transactions = base_q.order_by(Transaction.date).all()

    # Bucket transactions by period label
    from collections import defaultdict

    buckets: dict[str, dict] = defaultdict(
        lambda: {"income": 0.0, "expenses": 0.0, "sort_key": ""}
    )

    for t in transactions:
        raw_date = t.date or ""
        # Derive period label from the ISO date prefix
        try:
            parsed = date.fromisoformat(raw_date[:10])
            if group_by == "month":
                label = parsed.strftime("%b %Y")
                sort_key = parsed.strftime("%Y-%m")
            elif group_by == "week":
                # ISO week label: "Week 14, 2026"
                iso = parsed.isocalendar()
                label = f"Wk {iso.week:02d} {iso.year}"
                sort_key = f"{iso.year}-{iso.week:02d}"
            else:
                label = parsed.strftime("%b %d")
                sort_key = parsed.isoformat()
        except (ValueError, TypeError):
            label = raw_date
            sort_key = raw_date

        bucket = buckets[label]
        bucket["sort_key"] = sort_key
        if t.amount >= 0:
            bucket["income"] += t.amount
        else:
            bucket["expenses"] += abs(t.amount)

    trend = [
        {
            "period": label,
            "income": round(v["income"], 2),
            "expenses": round(v["expenses"], 2),
        }
        for label, v in sorted(buckets.items(), key=lambda kv: kv[1]["sort_key"])
    ]

    result = {"trend": trend, "group_by": group_by}
    set_cached(cache_key, result, ttl=TTL_ANALYSIS, user_id=current_user.id)
    return result


# ---------------------------------------------------------------------------
# GET /analysis/categories
# ---------------------------------------------------------------------------


@router.get("/categories")
def analysis_categories(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=10, ge=1, le=50),
    type: str = Query(default="expense", pattern="^(expense|income|all)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dr = _build_date_range_suffix(from_date, to_date)
    cache_key = f"analysis:categories:{current_user.id}:{dr}:{type}:{limit}"

    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    job_ids = _job_ids_for_user(db, current_user.id)
    if not job_ids:
        result = {"categories": [], "type": type}
        set_cached(cache_key, result, ttl=TTL_ANALYSIS, user_id=current_user.id)
        return result

    base_q = db.query(Transaction).filter(
        Transaction.job_id.in_(job_ids),
        Transaction.category.isnot(None),
    )
    base_q = _date_filter(base_q, from_date, to_date)

    if type == "expense":
        base_q = base_q.filter(Transaction.amount < 0)
    elif type == "income":
        base_q = base_q.filter(Transaction.amount > 0)

    transactions = base_q.all()

    from collections import defaultdict

    totals: dict[str, dict] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for t in transactions:
        cat = t.category or "Uncategorized"
        totals[cat]["amount"] += abs(t.amount)
        totals[cat]["count"] += 1

    categories = sorted(totals.items(), key=lambda kv: kv[1]["amount"], reverse=True)[
        :limit
    ]

    result = {
        "categories": [
            {"name": name, "amount": round(v["amount"], 2), "count": v["count"]}
            for name, v in categories
        ],
        "type": type,
    }

    set_cached(cache_key, result, ttl=TTL_ANALYSIS, user_id=current_user.id)
    return result


# ---------------------------------------------------------------------------
# GET /analysis/jobs/{job_id}/summary
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/summary")
def analysis_job_summary(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cache_key = f"analysis:job_summary:{job_id}"
    cached = get_cached(cache_key)
    if cached is not None:
        # Always verify ownership even on a cache hit
        if cached.get("user_id") != current_user.id:
            raise HTTPException(status_code=404, detail="Job not found")
        cached.pop("user_id", None)
        return cached

    job = (
        db.query(Job)
        .filter(Job.job_id == job_id, Job.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Category status counts
    status_rows = (
        db.query(Transaction.category_status, func.count(Transaction.id).label("cnt"))
        .filter(Transaction.job_id == job_id)
        .group_by(Transaction.category_status)
        .all()
    )
    cnt: dict[str, int] = {r.category_status: r.cnt for r in status_rows}

    category_counts = {
        "total": sum(cnt.values()),
        "done": cnt.get(CategoryStatus.done, 0),
        "pending": cnt.get(CategoryStatus.pending, 0),
        "failed": cnt.get(CategoryStatus.failed, 0),
    }

    # Transaction financial totals
    transactions = (
        db.query(Transaction.amount).filter(Transaction.job_id == job_id).all()
    )
    amounts = [r.amount for r in transactions]
    total_income = sum(a for a in amounts if a > 0)
    total_expenses = sum(abs(a) for a in amounts if a < 0)

    # Embed user_id in the stored payload for ownership check on cache hit
    result_with_uid = {
        "user_id": current_user.id,
        "job_id": job_id,
        "status": job.status,
        "filename": job.filename,
        "category_counts": category_counts,
        "transaction_summary": {
            "count": len(amounts),
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_flow": round(total_income - total_expenses, 2),
        },
    }

    # Use a longer TTL for completed/terminal jobs — their data never changes
    terminal = {
        JobStatus.completed,
        JobStatus.failed,
        JobStatus.extract_failed,
        JobStatus.categorize_failed,
    }
    ttl = TTL_JOB_SUMMARY if job.status in terminal else TTL_ANALYSIS
    set_cached(cache_key, result_with_uid, ttl=ttl, user_id=current_user.id)

    result_with_uid.pop("user_id")
    return result_with_uid
