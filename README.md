# Bank Statement Analyzer

Full-stack app to upload bank statements, extract transactions, categorize spending with local LLMs, and explore financial insights through dashboards and chat.

## Project Structure

- `frontend/` - Next.js app for authentication, uploads, dashboards, jobs, transaction management, and chat UI.
- `backend/` - FastAPI API for auth, statement processing, background jobs, analytics, embeddings, and storage.

Detailed docs:
- Frontend: [frontend/README.md](frontend/README.md)
- Backend: [backend/README.md](backend/README.md)

## Architecture (High Level)

- `frontend` sends authenticated requests to `backend`.
- `backend` stores app data in PostgreSQL.
- File assets (uploaded PDFs and markdown artifacts) are stored in MinIO (S3-compatible).
- Background processing runs through RQ + Redis.
- Embeddings are stored/retrieved from ChromaDB.
- Ollama powers extraction/categorization and chat responses.

## Quick Start

1. Start infrastructure services:
   ```bash
   docker compose -f docker-compose.infra.yml up
   ```
2. Run backend in one terminal:
   - Follow `backend/README.md` for venv, migrations, API server, and worker.
3. Run frontend in another terminal:
   - Follow `frontend/README.md` for install and dev server.

## Full Docker Setup

To run the full stack via Docker (including app services), use:

```bash
docker compose up
```

## Environment

- Root `.env.example` contains sample environment variables.
- Copy to `.env` and adjust values for your machine/services.

## Notes

- Backend default local URL: `http://localhost:8000`
- Frontend default local URL: `http://localhost:3000`
- Frontend expects backend running locally unless configured otherwise.
