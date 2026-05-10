from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime

from models import Transaction
from services.embeddings import search_transactions
from services.llm import call_ollama


def _parse_month_key(raw_date: str) -> str | None:
    try:
        dt = datetime.fromisoformat(raw_date[:10])
        return dt.strftime("%Y-%m")
    except Exception:
        return None


def _safe_json_object(text: str) -> dict | None:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def build_insights_payload(
    transactions: list[Transaction],
    dismissed_ids: set[str],
    user_id: str,
) -> dict:
    expenses = [t for t in transactions if float(t.amount) < 0]
    abs_expenses = [abs(float(t.amount)) for t in expenses]
    monthly_totals: dict[str, float] = defaultdict(float)
    by_category: dict[str, float] = defaultdict(float)

    for t in expenses:
        amount = abs(float(t.amount))
        mk = _parse_month_key(t.date or "")
        if mk:
            monthly_totals[mk] += amount
        by_category[t.category or "Uncategorized"] += amount

    median = statistics.median(abs_expenses) if abs_expenses else 0.0
    stdev = statistics.pstdev(abs_expenses) if len(abs_expenses) > 1 else 0.0
    threshold = max(median * 2.5, median + (2 * stdev))

    anomalies = []
    for t in expenses:
        amount = abs(float(t.amount))
        if amount >= threshold and t.id not in dismissed_ids:
            anomalies.append(
                {
                    "transaction_id": t.id,
                    "date": t.date,
                    "description": t.description,
                    "category": t.category,
                    "amount": round(float(t.amount), 2),
                    "flag_reason": f"High spend outlier (>{threshold:.2f})",
                }
            )

    sorted_months = sorted(monthly_totals.items())
    forecast_next_month = (
        round(sum(v for _, v in sorted_months[-3:]) / min(3, len(sorted_months)), 2)
        if sorted_months
        else 0.0
    )

    top_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:5]
    budget_suggestions = [
        {
            "category": category,
            "current_monthly_average": round(
                (amount / max(len(sorted_months), 1)),
                2,
            ),
            "suggested_budget": round((amount / max(len(sorted_months), 1)) * 0.9, 2),
        }
        for category, amount in top_categories
    ]

    rag_summary = ""
    try:
        hits = search_transactions(
            query="high value spends recurring bills unusual expenses saving opportunities",
            user_id=user_id,
            top_k=8,
        )
        rag_summary = "\n".join(
            [
                f"- {h.get('document', '')}"
                for h in hits
            ]
        )
    except Exception:
        rag_summary = ""

    narrative = "Insights generated from transaction trends."
    if rag_summary:
        prompt = f"""
You are a personal finance assistant. Return ONLY valid JSON object:
{{
  "summary": "short paragraph",
  "actions": ["action 1", "action 2", "action 3"]
}}

Data:
- anomaly_count: {len(anomalies)}
- next_month_forecast: {forecast_next_month}
- top_categories: {json.dumps(top_categories)}
- context:
{rag_summary}
"""
        try:
            obj = _safe_json_object(call_ollama(prompt))
            if obj and isinstance(obj.get("summary"), str):
                narrative = obj["summary"]
                actions = obj.get("actions", [])
            else:
                actions = []
        except Exception:
            actions = []
    else:
        actions = []

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "anomalies": anomalies,
        "forecast": {
            "next_month_expense_forecast": forecast_next_month,
            "months_used": len(sorted_months),
        },
        "budget_suggestions": budget_suggestions,
        "summary": narrative,
        "recommended_actions": actions[:5] if isinstance(actions, list) else [],
    }
