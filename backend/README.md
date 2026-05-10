# Finance Tracker — Backend

FastAPI backend for the Bank Statement Analyzer. Handles PDF ingestion, LLM-powered transaction categorization, user authentication, and file asset delivery.

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | PostgreSQL · SQLAlchemy ORM · Alembic migrations |
| Auth | Cookie-based sessions (HTTP-only, SHA-256 token hashing, PBKDF2 passwords) |
| Background Jobs | [RQ](https://python-rq.org/) + Redis · `worker.py` |
| Object Storage | MinIO (S3-compatible) via `boto3` |
| PDF Extraction | [Docling](https://ds4sd.github.io/docling/) |
| LLM Integration | Ollama (local) — `deepseek-r1` for extraction & categorization |
| Embeddings | Ollama `nomic-embed-text` — on-prem sentence embeddings |
| Vector Store | [ChromaDB](https://www.trychroma.com/) (dedicated Docker service, HTTP client) |

---

## Local Development Setup

Ensure **Redis**, **PostgreSQL**, **MinIO**, **ChromaDB**, and **Ollama** are running before starting the server.

For local development the easiest way to spin up the infrastructure is:
```bash
docker compose -f docker-compose.infra.yml up
```
This starts Redis, PostgreSQL, MinIO, and ChromaDB — leaving the backend and worker to run natively.

You will also need the Ollama embedding model:
```bash
ollama pull nomic-embed-text
```

1. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Start the FastAPI dev server:**
   ```bash
   fastapi dev main.py
   ```

4. **Start the background worker** (separate terminal):
   ```bash
   python worker.py
   ```

5. **S3 garbage collector (safe dry-run by default):**
   ```bash
   python s3_gc_runner.py
   ```
   Apply deletions explicitly (defaults to 24 hours):
   ```bash
   python s3_gc_runner.py --apply --min-age-hours 24
   ```

---

## Project Structure

```
backend/
├── main.py              # App bootstrap, all API route definitions
├── auth.py              # Session auth: hashing, cookie helpers, get_current_user
├── models.py            # SQLAlchemy ORM models (User, Session, Job, Transaction)
├── db.py                # DB engine and SessionLocal factory
├── tasks.py             # RQ background tasks (process_pdf, retry_categorization)
├── worker.py            # Custom RQ worker process
├── storage.py           # S3/MinIO client, bucket init, key helpers
├── config.py            # Pydantic-settings config (env vars, defaults)
├── logger.py            # Logging configuration
├── alembic/             # Alembic migration environment and version scripts
└── services/
    ├── llm.py           # LLM integration: extraction & categorization prompts
    ├── pdf.py           # Docling PDF-to-markdown conversion
    ├── rules.py         # Rules-based pre-categorization (runs before LLM)
    └── embeddings.py    # Vector embeddings: ChromaDB client, upsert, search, delete
```

---

## API Reference

### Auth
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create account, sets session cookie |
| `POST` | `/auth/login` | Sign in, sets session cookie |
| `POST` | `/auth/logout` | Destroys session, clears cookie |
| `GET`  | `/auth/me` | Returns the current authenticated user |

### Upload
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Upload a PDF bank statement |

### Jobs
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/jobs` | List paginated jobs for the current user |
| `POST` | `/jobs` | Create a new job manually |
| `GET`  | `/jobs/{job_id}` | Get job status and metadata |
| `PATCH`| `/jobs/{job_id}` | Update job metadata (e.g., filename, status) |
| `DELETE`| `/jobs/{job_id}`| Delete a job and its associated transactions |
| `GET`  | `/categorize/retry/{job_id}` | Re-run LLM categorization on a job |
| `GET`  | `/jobs/{job_id}/assets/pdf` | Stream the original uploaded PDF |
| `GET`  | `/jobs/{job_id}/assets/markdown` | Stream the extracted markdown artifact |

### Transactions
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/jobs/{job_id}/transactions`| Get paginated transactions for a job |
| `POST` | `/jobs/{job_id}/transactions`| Create a new transaction manually |
| `PATCH`| `/jobs/{job_id}/transactions/{transaction_id}` | Update an existing transaction |
| `DELETE`| `/jobs/{job_id}/transactions/{transaction_id}` | Delete a specific transaction |
| `GET`  | `/transactions/{job_id}` | Get transactions for a job (Legacy) |

### Analysis
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/analysis/summary` | Global summary metrics (income, expenses, savings) |
| `GET`  | `/analysis/spending-trend` | Time-series data of spending trends |
| `GET`  | `/analysis/categories` | Breakdown of spending by category |
| `GET`  | `/analysis/jobs/{job_id}/summary`| Summary metrics for a specific job |

### System / Admin
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/reset` | Delete all jobs and transactions for the current user |
| `GET`  | `/healthy` | Health check |

### Chat / RAG
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Ask a natural-language question about your transactions; returns LLM answer + source transactions |

---

## Completed Features

- [x] **Cookie-based Auth:** Secure HTTP-only session cookies with PBKDF2 password hashing and SHA-256 token storage. All job/transaction endpoints are scoped to the authenticated user.
- [x] **Alembic Migrations:** Full migration history including the `users` and `sessions` tables with SQLAlchemy `MetaData` naming conventions for reliable constraint names.
- [x] **S3 Object Storage (MinIO):** S3-compatible storage for uploads, with automatic bucket initialization, per-worker temporary file cleanup, and markdown artifact upload post-processing.
- [x] **Rules-Based Pre-Categorization:** `services/rules.py` utilizes a structured configuration format to deterministically categorize well-known merchants before sending remaining transactions to the LLM, reducing latency and API costs.
- [x] **PDF & Markdown Asset Endpoints:** `/jobs/{id}/assets/pdf` and `/jobs/{id}/assets/markdown` stream job assets directly from S3 with ownership checks.
- [x] **30-Minute RQ Timeout:** Extended job timeout for large PDFs processed by slow local LLMs.
- [x] **Config Management:** Migrated to `pydantic-settings` for type-safe, centralized, and environment-based configuration management.
- [x] **Dashboard Endpoints:** Aggregated reporting endpoints (spending by category, income vs. expenses, date ranges) optimized with user-specific caching and automatic invalidation on data changes.
- [x] **Docker Setup:** `docker-compose.yml` orchestrates API, worker, Redis, PostgreSQL, MinIO, ChromaDB, and frontend. `docker-compose.infra.yml` provides infra-only setup for native local development.
- [x] **Production Database:** Migrated from SQLite to PostgreSQL for production-ready persistence and robust concurrent access.
- [x] **Data Management (CRUD):** Comprehensive endpoints for full Create, Read, Update, and Delete operations on Jobs and Transactions.
- [x] **Vector Embeddings & RAG:** After each job completes, all transactions are embedded using Ollama `nomic-embed-text` and upserted into ChromaDB (HTTP service). Embeddings are user-scoped via metadata filtering. Deletions cascade — removing a job also removes its vectors.
- [x] **AI Chatbot API:** `POST /chat` endpoint that embeds the user's question, retrieves the top-K semantically similar transactions from ChromaDB (RAG), builds a grounded prompt, calls the Ollama LLM, strips `<think>` reasoning artifacts, and returns `{ answer, sources }`.
- [x] **S3 Garbage Collection:** Cron-friendly runner (`s3_gc_runner.py`) with dry-run default, age guard, and orphan PDF/markdown cleanup.
- [x] **Per-Job Bank Statement Summary:** After categorization completes, auto-generates a concise natural-language summary (with RAG support) for each job (total income, top expense categories, notable transactions) and saves it to the job record.
- [x] **Export to CSV:** `GET /jobs/{job_id}/export/transactions.csv` and `GET /jobs/export/transactions.csv` endpoints that stream a CSV of the user's transactions.
- [x] **Anomaly Detection:** Post-categorization background step that flags suspicious transactions — duplicates (same merchant + amount within N days), statistical outliers per category (Z-score / IQR), and sudden spending spikes — stored as a boolean `is_flagged` + `flag_reason` on the Transaction model.
- [x] **Spending Forecasting:** `GET /analysis/forecast` endpoint that uses linear regression (or exponential smoothing via `statsmodels`) on historical per-category monthly totals to predict next month's spend per category.
- [x] **Smart Budget Suggestions:** `GET /analysis/budget-suggestions` endpoint that sends the user's historical spending summary to the LLM and returns structured budget targets per category with justification.
---

## TODOs

> Planned improvements toward production-readiness.

- [ ] **Error Handling & Validation:** Standardize error responses and add request-level input validation.
- [ ] **Unit & Integration Tests:** `pytest` coverage for auth flows, job endpoints, and background tasks.

