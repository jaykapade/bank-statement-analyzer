import httpx
import json
import re
from logger import logger

OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL = "qwen2.5:7b"
MODEL = "deepseek-r1:7b"

# Max characters per extraction chunk (tune based on model context window)
# Keep low enough that Ollama can finish within its 180-second server timeout.
# local models are slow; 3500 chars ≈ ~60-90 seconds per chunk on most hardware.
MAX_CHUNK_CHARS = 3500
# Max transactions per categorization batch.
# Smaller = less output per call = less chance of truncated/malformed JSON.
CATEGORIZE_BATCH_SIZE = 8


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
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": True},
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
def call_with_retry(prompt: str, retries: int = 2):
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
def chunk_markdown(markdown: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
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
- For amounts: strip currency symbols (₹, $, £, €) and commas. If a statement uses separate debit/credit columns, use negative numbers for debits and positive for credits. "CR" suffix means credit (positive).
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

        normalized.append({"date": date, "description": description, "amount": amount})

    return normalized


# -----------------------------
# Categorize Transactions
# -----------------------------
CATEGORIZE_PROMPT_TEMPLATE = """
Categorize each transaction into exactly one of: Food, Shopping, Travel, Bills, Health, Other

Category definitions:
- Food: restaurants, cafes, food delivery (Swiggy, Zomato, Domino's), grocery stores, supermarkets, bakeries, juice bars
- Shopping: retail stores, e-commerce (Amazon, Flipkart, Myntra), clothing, electronics, D-Mart, departmental stores
- Travel: airlines, trains, bus tickets (RedBus, IRCTC), taxis (Ola, Uber), hotels, fuel stations, toll, travel agencies
- Bills: utility bills (electricity, water, gas), phone/internet recharge, insurance premiums, loan EMI, credit card payments, subscription services (Netflix, Spotify, Tinder)
- Health: hospitals, pharmacies, chemists, medical stores, clinics, fitness, diagnostics
- Other: payment wallets (Paytm, PhonePe, GPay) where purpose is unclear, bank fees, interest charges, unknown merchants, transfers

Rules:
- Return the "id" field exactly as given. Do not modify, omit, or generate new IDs.
- Use only these categories: Food, Shopping, Travel, Bills, Health, Other
- When in doubt between two categories, prefer the more specific one (e.g. pharmacy → Health, not Other)
- Subscriptions and recurring online services → Bills

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
    batch_size = CATEGORIZE_BATCH_SIZE

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
        prompt = CATEGORIZE_PROMPT_TEMPLATE.format(batch=json.dumps(batch))
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
