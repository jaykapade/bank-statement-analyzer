"""
routers/chat.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST /chat  — RAG-powered chatbot endpoint.

Flow
----
1. Authenticate via session cookie (same pattern as all other routers).
2. Embed the user's question with nomic-embed-text.
3. Retrieve the top-K most semantically similar transactions from ChromaDB
   (scoped to the authenticated user's data only).
4. Build a RAG prompt that injects those transactions as context.
5. Call the Ollama LLM (deepseek-r1) for the final answer.
6. Return { "answer": "...", "sources": [...] }

The endpoint is synchronous (not async/streaming) for simplicity; the Ollama
call already uses httpx streaming internally via call_ollama() in services/llm.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user
from config import settings
from logger import logger
from models import User
from services.embeddings import search_transactions
from services.llm import call_ollama

router = APIRouter(tags=["chat"])


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000,
        description="Natural language question about your transactions",
    )


class SourceTransaction(BaseModel):
    id: str
    document: str          # human-readable sentence built at embed time
    date: str
    category: str
    amount: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceTransaction]


# ──────────────────────────────────────────────────────────────────────────────
# RAG prompt template
# ──────────────────────────────────────────────────────────────────────────────

_RAG_PROMPT_TEMPLATE = """\
You are a helpful personal finance assistant. Answer the user's question based \
ONLY on the transaction records provided below. Be concise and specific. \
If the answer cannot be determined from the provided transactions, say so clearly \
rather than guessing.

--- TRANSACTION CONTEXT ---
{context}
--- END CONTEXT ---

User question: {question}

Answer:"""


def _build_rag_prompt(question: str, hits: list[dict]) -> str:
    if not hits:
        context = "No relevant transactions found."
    else:
        lines = []
        for i, hit in enumerate(hits, 1):
            meta = hit.get("metadata", {})
            lines.append(
                f"{i}. {hit['document']}  "
                f"[job: {meta.get('job_id', 'N/A')[:8]}...]"
            )
        context = "\n".join(lines)

    return _RAG_PROMPT_TEMPLATE.format(context=context, question=question)


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Ask a natural language question about your bank transactions.

    The backend will:
    - Semantically search your transactions for relevant context.
    - Use an LLM to generate a grounded answer from that context.
    """
    question = payload.message.strip()
    user_id = current_user.id

    # ── Step 1: Retrieve relevant transactions ──────────────────────────────
    try:
        hits = search_transactions(
            query=question,
            user_id=user_id,
            top_k=settings.chat_top_k,
        )
    except Exception as e:
        logger.error(f"[Chat] Embedding/search failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Embedding service unavailable. Make sure Ollama is running "
                "with the nomic-embed-text model."
            ),
        )

    logger.info(
        f"[Chat] Retrieved {len(hits)} transactions for user {user_id} "
        f"(query: {question[:60]!r})"
    )

    # ── Step 2: Build RAG prompt ────────────────────────────────────────────
    prompt = _build_rag_prompt(question, hits)

    # ── Step 3: LLM call ────────────────────────────────────────────────────
    try:
        raw_answer = call_ollama(prompt)
    except Exception as e:
        logger.error(f"[Chat] LLM call failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable. Make sure Ollama is running.",
        )

    # Strip common LLM preamble artefacts (<think>...</think> from deepseek-r1)
    import re
    answer = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL).strip()
    if not answer:
        answer = raw_answer.strip()

    # ── Step 4: Build sources list ──────────────────────────────────────────
    sources: list[SourceTransaction] = []
    for hit in hits:
        meta = hit.get("metadata", {})
        sources.append(
            SourceTransaction(
                id=hit["id"],
                document=hit["document"],
                date=str(meta.get("date", "")),
                category=str(meta.get("category", "")),
                amount=float(meta.get("amount", 0)),
            )
        )

    return ChatResponse(answer=answer, sources=sources)
