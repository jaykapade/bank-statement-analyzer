"""
services/embeddings.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vector embedding helpers for the RAG chatbot feature.

Architecture
------------
- Embedding model : Ollama nomic-embed-text (on-prem, no API key needed)
- Vector store    : ChromaDB HTTP server (dedicated Docker service, chromadb/chroma)
- User isolation  : every document is tagged with `user_id`; all queries are
                    filtered with `where={"user_id": user_id}` so users never
                    see each other's transactions.

Public API
----------
embed_text(text)                                → list[float]
upsert_transactions(txn_dicts, user_id)         → None
search_transactions(query, user_id, top_k)      → list[dict]
delete_job_transactions(job_id)                 → None
delete_user_transactions(user_id)               → None
"""

from __future__ import annotations

import httpx
import chromadb

from config import settings
from logger import logger

# ──────────────────────────────────────────────────────────────────────────────
# ChromaDB client (singleton — one per process)
# ──────────────────────────────────────────────────────────────────────────────
_chroma_client: chromadb.HttpClient | None = None
_chroma_collection: chromadb.Collection | None = None


def _get_client() -> chromadb.HttpClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        logger.info(
            f"[Embeddings] Connected to ChromaDB at "
            f"{settings.chroma_host}:{settings.chroma_port}"
        )
    return _chroma_client


def get_chroma_collection() -> chromadb.Collection:
    """
    Return (and lazily create) the shared ChromaDB collection.

    We use cosine distance because nomic-embed-text produces normalised vectors
    that compare best under cosine similarity.
    """
    global _chroma_collection
    if _chroma_collection is None:
        client = _get_client()
        _chroma_collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"[Embeddings] Using collection '{settings.chroma_collection}' "
            f"({_chroma_collection.count()} docs)"
        )
    return _chroma_collection


# ──────────────────────────────────────────────────────────────────────────────
# Ollama embedding call
# ──────────────────────────────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """
    Call Ollama's /api/embeddings endpoint and return the embedding vector.

    Raises on network/model errors so callers can decide whether to retry or
    treat the embedding step as non-fatal.
    """
    response = httpx.post(
        settings.ollama_embed_url,
        json={"model": settings.ollama_embed_model, "prompt": text},
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not embedding or not isinstance(embedding, list):
        raise ValueError(
            f"Unexpected Ollama embed response (no 'embedding' key): {data}"
        )
    return embedding


# ──────────────────────────────────────────────────────────────────────────────
# Document text builder
# ──────────────────────────────────────────────────────────────────────────────

def _build_document_text(txn: dict) -> str:
    """
    Produce a rich, human-readable sentence for a transaction so that the
    embedding captures semantic meaning beyond just the raw field values.

    Example output:
        "2024-01-15 | Swiggy Food Delivery | -450.00 | Food & Dining"
    """
    amount = txn.get("amount", 0)
    sign = "spent" if float(amount) < 0 else "received"
    abs_amount = abs(float(amount))
    category = txn.get("category") or "Uncategorized"
    description = txn.get("description", "").strip() or "Unknown"
    date = txn.get("date", "")

    return (
        f"On {date}, {sign} ₹{abs_amount:.2f} "
        f"for '{description}' (category: {category})"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Upsert transactions
# ──────────────────────────────────────────────────────────────────────────────

def upsert_transactions(txn_dicts: list[dict], user_id: str) -> None:
    """
    Embed each transaction and upsert into ChromaDB.

    - Idempotent: uses transaction `id` as the ChromaDB document ID, so
      re-running after a worker retry won't create duplicates.
    - Batch size: Ollama processes one embedding at a time; we batch the
      ChromaDB upsert so we make fewer round-trips to the vector store.

    Args:
        txn_dicts: list of dicts with keys: id, date, description, amount, category
        user_id:   the owning user's ID (used for isolation in queries)
    """
    if not txn_dicts:
        return

    collection = get_chroma_collection()
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for txn in txn_dicts:
        doc_text = _build_document_text(txn)
        try:
            vector = embed_text(doc_text)
        except Exception as e:
            logger.warning(
                f"[Embeddings] Skipping txn {txn.get('id')} — embed failed: {e}"
            )
            continue

        ids.append(str(txn["id"]))
        embeddings.append(vector)
        documents.append(doc_text)
        metadatas.append(
            {
                "user_id": user_id,
                "job_id": str(txn.get("job_id", "")),
                "date": str(txn.get("date", "")),
                "category": str(txn.get("category") or "Uncategorized"),
                "amount": float(txn.get("amount", 0)),
            }
        )

    if ids:
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"[Embeddings] Upserted {len(ids)} vectors for user {user_id}")


# ──────────────────────────────────────────────────────────────────────────────
# Semantic search
# ──────────────────────────────────────────────────────────────────────────────

def search_transactions(
    query: str,
    user_id: str,
    top_k: int | None = None,
) -> list[dict]:
    """
    Embed `query` and return the top-K most semantically similar transactions
    belonging to `user_id`.

    Returns a list of dicts with keys:
        id, document (text), distance, metadata (date, category, amount, job_id)
    """
    k = top_k or settings.chat_top_k
    collection = get_chroma_collection()

    # Guard: ChromaDB raises if n_results > collection size
    total = collection.count()
    if total == 0:
        logger.info("[Embeddings] Collection is empty — no results to return")
        return []

    k = min(k, total)

    try:
        query_vector = embed_text(query)
    except Exception as e:
        logger.error(f"[Embeddings] Failed to embed query: {e}")
        raise

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k,
        where={"user_id": user_id},
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for i, doc_id in enumerate(results["ids"][0]):
        hits.append(
            {
                "id": doc_id,
                "document": results["documents"][0][i],
                "distance": results["distances"][0][i],
                "metadata": results["metadatas"][0][i],
            }
        )
    return hits


# ──────────────────────────────────────────────────────────────────────────────
# Cleanup helpers
# ──────────────────────────────────────────────────────────────────────────────

def delete_job_transactions(job_id: str) -> None:
    """
    Remove all ChromaDB vectors whose metadata.job_id matches `job_id`.
    Called when a job is deleted via the REST API.
    """
    try:
        collection = get_chroma_collection()
        collection.delete(where={"job_id": job_id})
        logger.info(f"[Embeddings] Deleted vectors for job {job_id}")
    except Exception as e:
        # Non-fatal — the DB row is already gone, this is best-effort cleanup
        logger.warning(f"[Embeddings] Failed to delete vectors for job {job_id}: {e}")


def delete_user_transactions(user_id: str) -> None:
    """
    Remove all ChromaDB vectors belonging to `user_id`.
    Useful for GDPR-style account deletion.
    """
    try:
        collection = get_chroma_collection()
        collection.delete(where={"user_id": user_id})
        logger.info(f"[Embeddings] Deleted all vectors for user {user_id}")
    except Exception as e:
        logger.warning(
            f"[Embeddings] Failed to delete vectors for user {user_id}: {e}"
        )
