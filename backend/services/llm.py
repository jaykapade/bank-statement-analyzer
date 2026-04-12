import httpx
import json
import re
from logger import logger
from config import settings
from services.rules import CATEGORY_DEFINITIONS, build_category_prompt_block


# -----------------------------
# Core Ollama Call
# -----------------------------
def call_ollama(prompt: str) -> str:
    """
    Call Ollama using streaming mode (stream=True).

    Why streaming? Ollama has a server-side task timeout (~180s) that fires when a
    non-streaming request sits in the queue or takes too long to complete. With
    streaming, the connection stays live as tokens arrive, so that timeout never
    triggers — regardless of how long total generation takes.
    """
    try:
        tokens: list[str] = []
        with httpx.stream(
            "POST",
            settings.ollama_url,
            json={"model": settings.ollama_model, "prompt": prompt, "stream": True},
            timeout=None,  # no client-side limit; Ollama server controls its own timeout
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                tokens.append(data.get("response", ""))
                if data.get("done", False):
                    break

        return "".join(tokens)

    except Exception as e:
        logger.error(f"Ollama API error: {e}")
        raise


# -----------------------------
# JSON Cleaning
# -----------------------------
def clean_json_response(text: str) -> str:
    """
    Removes ```json ... ``` wrappers from LLM output
    """
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def extract_json_objects(text: str) -> list | None:
    """
    Fallback: when the LLM returns a syntactically broken JSON array, attempt
    to salvage individual valid JSON objects from the raw text using regex.
    This handles the common case where the array is well-formed up until the
    last object, which may be truncated or have a dangling comma.
    """
    # Find every {...} blob (non-greedy won't work across newlines — use re.DOTALL)
    raw_objects = re.findall(r"\{[^{}]+\}", text, re.DOTALL)
    salvaged = []
    for raw in raw_objects:
        try:
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                continue  # skip non-dict objects (nested arrays, primitives, etc.)
            salvaged.append(obj)
        except Exception:
            pass  # skip objects that are themselves malformed
    return salvaged if salvaged else None


def safe_json_loads(text: str):
    cleaned = clean_json_response(text)
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"JSON parse failed: {e}")

    # Try salvaging individual objects from broken output
    salvaged = extract_json_objects(cleaned)
    if salvaged:
        logger.warning(f"Salvaged {len(salvaged)} object(s) from malformed JSON")
        return salvaged

    return None


# -----------------------------
# Retry Wrapper
# -----------------------------
def call_with_retry(prompt: str, retries: int = settings.llm_retry_attempts):
    for attempt in range(retries):
        raw_output = call_ollama(prompt)

        # Empty response means Ollama timed out or returned nothing — retry
        if not raw_output or not raw_output.strip():
            logger.warning(
                f"Retrying LLM call (attempt {attempt + 1}) — empty response"
            )
            continue

        parsed = safe_json_loads(raw_output)

        # ✅ valid JSON (including empty list)
        if parsed is not None:
            return parsed

        logger.warning(f"Retrying LLM call (attempt {attempt + 1})")

    logger.error("LLM failed after retries")
    return None  # ❌ true failure


# -----------------------------
# Markdown Chunking (table-aware)
# -----------------------------
def chunk_markdown(markdown: str, max_chars: int = settings.llm_max_chunk_chars) -> list[str]:
    """
    Split markdown into chunks of at most max_chars while preserving table structure.

    Markdown tables look like:
        | Date | Description | Amount |
        |------|-------------|--------|   <- separator row
        | ...  | ...         | ...    |  <- data rows

    Naive splitting on blank lines (or mid-table) would detach the header from data
    rows, making the LLM unable to identify columns. This chunker:
    - Detects when it's inside a table (lines starting with '|')
    - Tracks the header + separator as `table_header`
    - Re-injects `table_header` at the top of every new chunk when splitting mid-table
    - Falls back to line-by-line splitting for non-table content
    """
    lines = markdown.splitlines()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    in_table = False
    table_header: list[str] = []  # header row(s) + separator to re-inject on split

    def is_table_row(line: str) -> bool:
        return line.strip().startswith("|")

    def is_separator_row(line: str) -> bool:
        # e.g. |---|:---:|---| or |--- |
        return bool(re.match(r"^\|[-:\s|]+\|$", line.strip()))

    def flush_chunk():
        nonlocal current, current_len
        if current:
            chunks.append("\n".join(current))
        current = []
        current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for the newline

        if is_table_row(line):
            if not in_table:
                # Entering a table — flush any pending non-table content first
                flush_chunk()
                in_table = True
                table_header = []

            # Accumulate header rows (header + separator) before any data rows
            if not table_header or is_separator_row(line):
                table_header.append(line)
                current.append(line)
                current_len += line_len
            else:
                # It's a data row — check if we need to split
                if current_len + line_len > max_chars and current:
                    flush_chunk()
                    # Re-inject table header so the LLM has column context
                    current = list(table_header)
                    current_len = sum(len(h) + 1 for h in table_header)

                current.append(line)
                current_len += line_len
        else:
            if in_table:
                # Leaving a table — flush it
                flush_chunk()
                in_table = False
                table_header = []

            # Non-table line: split on size like before
            if current_len + line_len > max_chars and current:
                flush_chunk()

            current.append(line)
            current_len += line_len

    flush_chunk()
    return [c for c in chunks if c.strip()]


# -----------------------------
# Extract Transactions
# -----------------------------
EXTRACT_PROMPT_TEMPLATE = """
You are a financial data extraction assistant. You will be given a portion of a bank statement converted from a PDF. It may contain noise such as bank logos, headers, footers, account holder info, opening/closing balances, legal disclaimers. Ignore all of that.

Your only job is to extract the individual transaction rows from this portion.

A transaction row always has:
- A date (in any format — normalize it to YYYY-MM-DD)
- A description or merchant name
- A monetary amount (may have currency symbols, commas, or be split into debit/credit columns)

Rules:
- IGNORE: page headers, bank name, account number, branch info, opening balance, closing balance, total rows, legal text, image captions, any row without a clear date
- IGNORE: the STATEMENT SUMMARY section — this contains aggregate figures like "Previous Balance", "Purchases / Charges", "Cash Advances", "Payments / Credits", and "Total Amount Due". These are summary totals with NO associated date or serial number — they are NOT individual transactions.
- IGNORE: the CREDIT SUMMARY section — it contains credit limit and available credit figures, not transactions.
- IGNORE: any amount that appears in running/paragraph text (not inside a proper table row) without both a date AND a serial/transaction number. For example, standalone amounts like "61,165.81", "1,33,291.53", "1,39,471.36" are statement-level totals — skip them entirely.
- IGNORE: any table that shows hypothetical or illustrative examples — these include "Interest calculation", "Minimum Amount Due Calculation", "Late Payment Charges Calculation", or any table with headings like "SL. No", "Transaction", containing example purchases/fees used to illustrate bank policy
- IGNORE: EMI / Personal Loan summary tables showing installment schedules, not actual transactions
- For amounts: strip currency symbols (₹, $, £, €) and commas. The sign is critical — NEVER return all amounts as positive.
- Debit/outflow/spend rules:
  - Debit column populated -> negative
  - Withdrawal / purchase / charge / fee / cash advance / ATM / POS / DR / debit -> negative
  - On credit-card statements, card spends, charges, fees, finance charges, EMI debits, and cash withdrawals are negative
- Credit/inflow/refund rules:
  - Credit column populated -> positive
  - Deposit / salary / refund / reversal / cashback / interest credited / payment received / CR / credit -> positive
  - On credit-card statements, card bill payments, refunds, reversals, and cashback are positive
- If a row has separate debit and credit columns, exactly one populated column determines the sign. Ignore blank/zero column values.
- If the statement shows a suffix/prefix such as CR, DR, CREDIT, DEBIT, +, or -, preserve that direction in the numeric amount.
- Do not infer sign from running balance. Use the transaction row's debit/credit indicators only.
- Good examples:
  - "Amazon Purchase | Debit 1,250.00" -> amount -1250.00
  - "Salary Credit | Credit 52,000.00" -> amount 52000.00
  - "Card Payment Received | CR 8,000.00" -> amount 8000.00
  - "ATM Withdrawal | DR 2,000.00" -> amount -2000.00
- Normalize all dates to YYYY-MM-DD format regardless of input format (e.g. 01 Jan 2024, 2024/01/01, 01-01-24)
- If description is unclear, use the closest readable text from that row
- Return an empty array [] if no valid transactions are found in this portion

Return ONLY a valid JSON array, no explanation, no markdown code fences:
[
  {{
    "date": "YYYY-MM-DD",
    "description": "string",
    "amount": number
  }}
]

Bank statement portion:
{chunk}
"""


def extract_transactions(markdown: str):
    chunks = chunk_markdown(markdown)
    logger.info(f"[LLM] Extracting transactions from {len(chunks)} chunk(s)")

    all_raw: list = []
    had_failure = False

    for i, chunk in enumerate(chunks):
        logger.info(
            f"[LLM] Processing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)"
        )
        prompt = EXTRACT_PROMPT_TEMPLATE.format(chunk=chunk)
        result = call_with_retry(prompt)

        if result is None:
            logger.warning(f"[LLM] Chunk {i + 1} extraction failed, skipping")
            had_failure = True
            continue

        if isinstance(result, list):
            all_raw.extend(result)

    # If ALL chunks failed it's a true failure
    if not all_raw and had_failure:
        return None

    return normalize_transactions(all_raw)


# -----------------------------
# Normalize Data
# -----------------------------
NEGATIVE_DESCRIPTION_PATTERNS = [
    re.compile(r"\b(?:igst|cgst|sgst|utgst|gst)\b", re.IGNORECASE),
    re.compile(r"\bgst\s*(?:charge|fee|tax)?\b", re.IGNORECASE),
    re.compile(r"\btax(?:es)?\b", re.IGNORECASE),
]


def apply_amount_sign_heuristics(description: str, amount: float) -> float:
    """
    Correct common LLM sign mistakes using strong description cues.

    We keep this intentionally conservative and only flip signs for patterns
    that are overwhelmingly debit/outflow in statements.
    """
    if amount > 0:
        for pattern in NEGATIVE_DESCRIPTION_PATTERNS:
            if pattern.search(description):
                logger.info(
                    f"[LLM] Flipping amount to negative based on description cue: "
                    f"{description!r} ({amount})"
                )
                return -abs(amount)

    return amount


def normalize_transactions(transactions: list):
    """
    Cleans and normalizes each transaction from LLM output.
    - date: required — row is skipped if missing
    - amount: required — row is skipped if missing or unparseable
    - description: defaults to "unknown" if missing
    """
    normalized = []

    for t in transactions:
        # Guard: LLM salvage can occasionally return non-dict items
        if not isinstance(t, dict):
            logger.warning(f"Skipping non-dict transaction entry: {type(t)} {t!r}")
            continue

        # date is required
        raw_date = t.get("date")
        if raw_date in (None, "", "None"):
            logger.warning(f"Skipping transaction with no date: {t}")
            continue
        date = str(raw_date).strip()

        # amount is required
        raw_amount = t.get("amount")
        if raw_amount is None:
            logger.warning(f"Skipping transaction with no amount: {t}")
            continue
        try:
            amount = float(raw_amount)
        except (ValueError, TypeError):
            logger.warning(f"Skipping transaction with unparseable amount: {t}")
            continue

        # description can fall back
        raw_desc = t.get("description")
        description = (
            str(raw_desc).strip() if raw_desc not in (None, "", "None") else "unknown"
        )
        amount = apply_amount_sign_heuristics(description, amount)

        normalized.append({"date": date, "description": description, "amount": amount})

    return normalized


# -----------------------------
# Categorize Transactions
# -----------------------------
_CATEGORY_NAMES = list(CATEGORY_DEFINITIONS.keys())
_CATEGORY_PROMPT_BLOCK = build_category_prompt_block()

CATEGORIZE_PROMPT_TEMPLATE = """
Categorize each transaction into exactly one of: {category_names}

Category definitions:
{category_definitions}

Rules:
- Return the "id" field exactly as given. Do not modify, omit, or generate new IDs.
- Use only these categories: {category_names}
- When in doubt between two categories, prefer the more specific one (e.g. pharmacy → Health, not Other)
- Subscriptions and recurring online services → Bills
- Credit card bill payments, utility payments, recharge, insurance, and EMI/NACH/ECS debits -> Bills
- Wallet rails like Paytm, PhonePe, GPay, UPI, bank transfer, NEFT, IMPS, RTGS, or generic transfer descriptions -> Other unless the merchant purpose is explicitly clear
- Use amount sign as supporting context only:
  - Negative amounts are usually spending/outflow
  - Positive amounts are usually salary, refund, reversal, cashback, payment receipt, or transfer-in
  - Do not classify purely by sign if the merchant clearly indicates a better category

Return ONLY a valid JSON array, no explanation, no markdown code fences:
[
  {{
    "id": "uuid-string-exactly-as-given",
    "category": "string"
  }}
]

Transactions:
{batch}
"""


def categorize_transactions(transactions: list):
    if not transactions:
        return []

    all_categorized: list = []
    had_failure = False
    batch_size = settings.llm_categorize_batch_size

    batches = [
        transactions[i : i + batch_size]
        for i in range(0, len(transactions), batch_size)
    ]
    logger.info(
        f"[LLM] Categorizing {len(transactions)} transaction(s) in {len(batches)} batch(es)"
    )

    for i, batch in enumerate(batches):
        logger.info(
            f"[LLM] Categorizing batch {i + 1}/{len(batches)} ({len(batch)} transactions)"
        )
        prompt = CATEGORIZE_PROMPT_TEMPLATE.format(
            category_names=", ".join(_CATEGORY_NAMES),
            category_definitions=_CATEGORY_PROMPT_BLOCK,
            batch=json.dumps(batch),
        )
        result = call_with_retry(prompt)

        if result is None:
            logger.warning(f"[LLM] Categorization batch {i + 1} failed, skipping")
            had_failure = True
            continue

        if isinstance(result, list):
            all_categorized.extend(result)

    if not all_categorized and had_failure:
        return None

    return all_categorized
