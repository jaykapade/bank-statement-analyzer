import sys
import multiprocessing
import multiprocessing.context

# RQ's scheduler.py calls get_context('fork') at import time.
# Windows doesn't support 'fork' so we intercept the call and redirect to 'spawn'.
if sys.platform == "win32":
    _original_get_context = multiprocessing.context.BaseContext.get_context

    def _patched_get_context(self, method=None):
        if method == "fork":
            method = "spawn"
        return _original_get_context(self, method)

    multiprocessing.context.BaseContext.get_context = _patched_get_context

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from logger import logger
from storage import init_bucket

from routers.admin import router as admin_router
from routers.analysis import router as analysis_router
from routers.auth import router as auth_router
from routers.jobs import router as jobs_router
from routers.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_bucket()
        logger.info("S3 bucket initialized")
    except Exception as e:
        logger.error(f"Failed to initialize S3 bucket: {e}", exc_info=True)
        raise  # fail fast — don't start the app without storage
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(upload_router)
app.include_router(admin_router)
app.include_router(analysis_router)


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Service temporarily unavailable, try later"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/healthy", tags=["health"])
def healthy():
    return {"status": "healthy"}
