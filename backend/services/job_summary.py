from datetime import datetime
from decimal import Decimal

from logger import logger
from models import CategoryStatus, Job, Transaction
from services.brief_rag import generate_job_brief_rag

ZERO = Decimal("0")


def _fmt_money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _build_summary_brief(
    transactions: list[Transaction],
    income: Decimal,
    expenses: Decimal,
    net: Decimal,
    done: int,
    pending: int,
    failed: int,
) -> str:
    if not transactions:
        return "No transactions extracted yet."

    expense_by_cat: dict[str, Decimal] = {}
    income_by_cat: dict[str, Decimal] = {}
    for t in transactions:
        cat = (t.category or "Uncategorized").strip() or "Uncategorized"
        amt = t.amount or ZERO
        if amt < 0:
            expense_by_cat[cat] = expense_by_cat.get(cat, ZERO) + abs(amt)
        elif amt > 0:
            income_by_cat[cat] = income_by_cat.get(cat, ZERO) + amt

    top_expense_cat, top_expense_amt = ("None", ZERO)
    if expense_by_cat:
        top_expense_cat, top_expense_amt = max(expense_by_cat.items(), key=lambda kv: kv[1])

    top_income_cat, top_income_amt = ("None", ZERO)
    if income_by_cat:
        top_income_cat, top_income_amt = max(income_by_cat.items(), key=lambda kv: kv[1])

    uncategorized_count = sum(1 for t in transactions if not t.category)
    uncategorized_pct = (uncategorized_count / len(transactions)) * 100

    good_parts: list[str] = []
    if net >= 0:
        good_parts.append(
            f"You are cash-flow positive in this statement with a net of {_fmt_money(net)}."
        )
    if top_income_amt > 0:
        good_parts.append(
            f"Your strongest inflow comes from {top_income_cat} ({_fmt_money(top_income_amt)})."
        )
    if done == len(transactions):
        good_parts.append("All transactions are categorized, which makes analysis more reliable.")

    bad_parts: list[str] = []
    if net < 0:
        bad_parts.append(f"Net flow is negative at {_fmt_money(net)}.")
    if pending > 0 or failed > 0:
        bad_parts.append(f"{pending + failed} transactions still need category attention.")
    if uncategorized_pct >= 20:
        bad_parts.append(
            f"Uncategorized share is high ({uncategorized_count} of {len(transactions)})."
        )

    improve_parts: list[str] = []
    if top_expense_amt > 0 and top_expense_cat != "None":
        improve_parts.append(
            f"Review {top_expense_cat}, your largest spend bucket at {_fmt_money(top_expense_amt)}, for possible trims."
        )
    if pending > 0 or failed > 0 or uncategorized_pct >= 20:
        improve_parts.append("Improve category coverage to get sharper trend and budget insights.")

    if not good_parts:
        good_parts.append("Your income and expense pattern is available for review.")
    if not bad_parts:
        bad_parts.append("No major risk flags stand out in this statement.")
    if not improve_parts:
        improve_parts.append("Keep tracking this pattern over time to spot trend changes early.")

    total = len(transactions)
    expense_share_note = ""
    if top_expense_amt > 0 and expenses > 0:
        share = (top_expense_amt / expenses) * 100
        expense_share_note = (
            f"{top_expense_cat} was the largest spend bucket at about {share:.0f}% of total expenses. "
        )

    return (
        f"{expense_share_note}"
        f"{' '.join(good_parts)} "
        f"{' '.join(bad_parts)} "
        f"{' '.join(improve_parts)} "
        f"Current coverage: {done}/{total} categorized."
    ).strip()


def recompute_job_summary(session, job_id: str, include_rag_brief: bool = False) -> None:
    session.flush()
    transactions = session.query(Transaction).filter(Transaction.job_id == job_id).all()
    job = session.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        return

    income = sum((t.amount for t in transactions if t.amount and t.amount > 0), ZERO)
    expenses = sum(
        (abs(t.amount) for t in transactions if t.amount and t.amount < 0),
        ZERO,
    )

    done = 0
    pending = 0
    failed = 0
    for t in transactions:
        if t.category_status == CategoryStatus.done or (
            t.category_status is None and t.category
        ):
            done += 1
        elif t.category_status == CategoryStatus.failed:
            failed += 1
        else:
            pending += 1

    net = income - expenses
    summary_brief_rules = _build_summary_brief(
        transactions=transactions,
        income=income,
        expenses=expenses,
        net=net,
        done=done,
        pending=pending,
        failed=failed,
    )
    summary_brief = summary_brief_rules
    summary_brief_source = "rules"
    if include_rag_brief and job.user_id:
        logger.info(f"[Summary] Attempting RAG brief for job {job_id}")
        summary_brief_rag = generate_job_brief_rag(
            job_id=job_id,
            user_id=job.user_id,
            income=income,
            expenses=expenses,
            net=net,
            total_rows=len(transactions),
            pending=pending,
            failed=failed,
        )
        if summary_brief_rag:
            summary_brief = summary_brief_rag
            summary_brief_source = "rag"
            logger.info(f"[Summary] RAG brief generated for job {job_id}")
        else:
            logger.info(
                f"[Summary] RAG brief unavailable for job {job_id}, using rules fallback"
            )

    session.query(Job).filter(Job.job_id == job_id).update(
        {
            "summary_transaction_count": len(transactions),
            "summary_income_total": income,
            "summary_expense_total": expenses,
            "summary_net_total": net,
            "summary_done_count": done,
            "summary_pending_count": pending,
            "summary_failed_count": failed,
            "summary_brief": summary_brief,
            "summary_brief_source": summary_brief_source,
            "summary_last_computed_at": datetime.utcnow(),
        },
        synchronize_session=False,
    )
