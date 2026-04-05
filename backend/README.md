# Finance Tracker Backend

This is the backend service for the Finance Tracker application, built with FastAPI, SQLite, and RQ for background job processing.

## Tech Stack Overview

- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) for building APIs.
- **Database:** SQLite (for local development) with **SQLAlchemy** (ORM) and **Alembic** (migrations).
- **Background Jobs:** [RQ (Redis Queue)](https://python-rq.org/) combined with a `worker.py` script to handle asynchronous tasks like PDF parsing and LLM categorizations.
- **Object Storage:** MinIO (S3-compatible object storage) using `boto3` for distributing file uploads reliably to background workers.
- **PDF Extraction:** [Docling](https://ds4sd.github.io/docling/) for robust extraction of text and tables from uploaded PDF files.
- **LLM Integration:** Ollama (or other LLMs) used via local models to categorize and structure financial transactions.

## Local Development Setup

Ensure you have a Redis server running locally or via Docker and Ollama accessible on its default port. You will also need MinIO running locally for S3 storage.

1. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Start the FastAPI Dev Server:**
   ```bash
   fastapi dev main.py
   ```

4. **Start the Background Worker:**
   In a separate terminal, to process PDF jobs:
   ```bash
   python worker.py
   ```

## Project Structure

- `main.py`: Bootstraps the application and registers API routes.
- `models.py`: SQLAlchemy ORM models (Transactions, Jobs, etc).
- `db.py`: Database connection and session management.
- `alembic/`: Database migration definitions.
- `tasks.py`: Background job tasks run by the RQ worker. The worker downloads PDFs from MinIO to a temporary file before processing, then cleans it up.
- `worker.py`: Custom RQ worker process script handling job processing.
- `services/`: Contains specific business logic services (e.g., `llm.py`, `pdf.py`).
- `storage.py`: S3 bucket initialization and configurations.
- `logger.py`: Standard logging configurations.

---

## Completed Features

- **S3 Object Storage (MinIO):** Fully implemented S3-compatible service for handling document uploads reliably across distributed workers. Features include automatic bucket initialization, file upload handling, secure worker downloads to temporary files with guaranteed cleanup, and orphaned file deletion upon application reset.

## TODOs for Future Setups

> **Note:** The following are planned improvements and architectural changes meant to make the service production-ready.

- [ ] **S3 Garbage Collection:** Implement a background worker that runs on a schedule (e.g., off-peak hours) to identify and delete S3 objects that have no corresponding job record in the database, with a configurable age threshold to protect in-flight uploads.
- [ ] **Docker Setup:** Update and verify the `Dockerfile` and `docker-compose.yml` to properly orchestrate the API, RQ worker, Redis, Database, and MinIO with optimal configurations.
- [ ] **Configuration Management:** Implement structured application settings using `pydantic-settings` to securely and cleanly load sensitive credentials, database paths, and API endpoints from Environment Variables rather than hardcoding.
- [ ] **Proper Database for Production:** Switch out SQLite for PostgreSQL or MySQL when moving to a production environment.
- [ ] **Unit and Integration Tests:** Set up `pytest` to validate core endpoints and background job execution.
