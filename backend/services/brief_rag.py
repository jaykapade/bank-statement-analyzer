import re
import json
from decimal import Decimal

from logger import logger
from services.embeddings import search_transactions
from services.llm import call_ollama


def _strip_think(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return cleaned or text.strip()


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"`", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_json_object(text: str) -> dict | None:
    cleaned = _strip_think(text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _format_structured_brief(parts: dict) -> str | None:
    ch = _strip_markdown(str(parts.get("category_highlight", "")).strip())
    good = _strip_markdown(str(parts.get("good", "")).strip())
    watch = _strip_markdown(str(parts.get("watch_outs", "")).strip())
    improve = _strip_markdown(str(parts.get("can_improve", "")).strip())
    if not any([ch, good, watch, improve]):
        return None
    parts_out: list[str] = []
    parts_out.append(ch or "No strong category trend was identified in this statement.")
    parts_out.append(good or "Overall this statement looks stable based on available rows.")
    parts_out.append(watch or "No major risk flags were detected in this statement.")
    parts_out.append(improve or "Continue tracking month over month to improve planning confidence.")
    return " ".join(parts_out)


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def generate_job_brief_rag(
    *,
    job_id: str,
    user_id: str,
    income: Decimal,
    expenses: Decimal,
    net: Decimal,
    total_rows: int,
    pending: int,
    failed: int,
) -> str | None:
    logger.info(f"[Brief-RAG] Starting brief generation for job {job_id}")
    try:
        hits = search_transactions(
            query=(
                "summarize this job spending patterns top expense categories "
                "income sources unusual transactions risks positives"
            ),
            user_id=user_id,
            top_k=20,
            job_id=job_id,
        )
    except Exception as exc:
        logger.warning(f"[Brief-RAG] Retrieval failed for job {job_id}: {exc}")
        return None

    logger.info(f"[Brief-RAG] Retrieved {len(hits)} semantic hits for job {job_id}")
    if not hits:
        return None

    context_lines: list[str] = []
    for i, hit in enumerate(hits[:12], 1):
        meta = hit.get("metadata", {})
        context_lines.append(
            f"{i}. {hit.get('document', '')} | date={meta.get('date','')} | "
            f"category={meta.get('category','')} | amount={meta.get('amount','')}"
        )
    context = "\n".join(context_lines)

    prompt = f"""
You are a personal finance analyst. Create a brief, factual summary for one bank-statement job.
Return ONLY valid JSON object with keys:
- category_highlight
- good
- watch_outs
- can_improve
Style rules:
- Keep the content concise but natural and user-friendly.
- Avoid markdown, bullets, labels, or key names in values.
- Mention concrete numbers when useful (percentages, net flow, count).

Metrics:
- total_rows: {total_rows}
- total_income: {_money(income)}
- total_expenses: {_money(expenses)}
- net_flow: {_money(net)}
- rows_needing_attention: {pending + failed}

Representative transactions:
{context}
"""
    try:
        raw = call_ollama(prompt)
        parsed = _extract_json_object(raw)
        if parsed:
            formatted = _format_structured_brief(parsed)
            if formatted:
                logger.info(
                    f"[Brief-RAG] Structured brief generated for job {job_id} (chars={len(formatted)})"
                )
                return formatted

        answer = _strip_markdown(_strip_think(raw))
        logger.info(
            f"[Brief-RAG] LLM returned brief for job {job_id} (chars={len(answer) if answer else 0})"
        )
        if not answer:
            return None
        return (
            f"{answer} Review high-value debits and any unclear merchant labels. "
            "Improving category clarity over time will make trend tracking more reliable."
        )
    except Exception as exc:
        logger.warning(f"[Brief-RAG] LLM generation failed for job {job_id}: {exc}")
        return None
