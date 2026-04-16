# Finance Tracker — Backend

FastAPI backend for the Bank Statement Analyzer. Handles PDF ingestion, LLM-powered transaction categorization, user authentication, and file asset delivery.

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | SQLite (dev) · SQLAlchemy ORM · Alembic migrations |
| Auth | Cookie-based sessions (HTTP-only, SHA-256 token hashing, `bcrypt` passwords) |
| Background Jobs | [RQ](https://python-rq.org/) + Redis · `worker.py` |
| Object Storage | MinIO (S3-compatible) via `boto3` |
| PDF Extraction | [Docling](https://ds4sd.github.io/docling/) |
| LLM Integration | Ollama (local) for transaction categorization |

---

## Local Development Setup

Ensure **Redis**, **MinIO**, and **Ollama** are running before starting the server.

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
├── logger.py            # Logging configuration
├── alembic/             # Alembic migration environment and version scripts
└── services/
    ├── llm.py           # LLM integration for transaction categorization
    ├── pdf.py           # Docling PDF-to-markdown conversion
    └── rules.py         # Rules-based pre-categorization (runs before LLM)
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

---

## Completed Features

- **Cookie-based Auth:** Secure HTTP-only session cookies with bcrypt password hashing and SHA-256 token storage. All job/transaction endpoints are scoped to the authenticated user.
- **Alembic Migrations:** Full migration history including the `users` and `sessions` tables with SQLAlchemy `MetaData` naming conventions for reliable constraint names.
- **S3 Object Storage (MinIO):** S3-compatible storage for uploads, with automatic bucket initialization, per-worker temporary file cleanup, and markdown artifact upload post-processing.
- **Rules-Based Pre-Categorization:** `services/rules.py` utilizes a structured configuration format to deterministically categorize well-known merchants before sending remaining transactions to the LLM, reducing latency and API costs.
- **PDF & Markdown Asset Endpoints:** `/jobs/{id}/assets/pdf` and `/jobs/{id}/assets/markdown` stream job assets directly from S3 with ownership checks.
- **30-Minute RQ Timeout:** Extended job timeout for large PDFs processed by slow local LLMs.
- **Config Management:** Migrated to `pydantic-settings` for type-safe, centralized, and environment-based configuration management.
- **Dashboard Endpoints:** Aggregated reporting endpoints (spending by category, income vs. expenses, date ranges) optimized with user-specific caching and automatic invalidation on data changes.
- **Docker Setup:** Orchestrates API, worker, Redis, DB, and MinIO via `docker-compose.yml`, including reliable container-to-host networking for local Ollama instances.
- **Production Database:** Migrated from SQLite to PostgreSQL for production-ready persistence and robust concurrent access.
- **Data Management (CRUD):** Comprehensive endpoints for full Create, Read, Update, and Delete operations on Jobs and Transactions.

---

## TODOs

> Planned improvements toward production-readiness.

- [ ] **S3 Garbage Collection:** Background task to prune S3 objects with no matching job record.
- [ ] **Error Handling & Validation:** Standardize error responses and add request-level input validation.
- [ ] **Unit & Integration Tests:** `pytest` coverage for auth flows, job endpoints, and background tasks.
