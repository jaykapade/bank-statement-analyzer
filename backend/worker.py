import os
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

from redis import Redis
from rq import Queue

# same env logic
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_conn = Redis(host=redis_host, port=6379)

# define queue — default RQ timeout is 180s which is too short for multi-chunk LLM jobs
queue = Queue(connection=redis_conn, default_timeout=900)

if __name__ == "__main__":
    # RQ's default Worker uses fork() which is not available on Windows.
    # SimpleWorker runs jobs in-process and is fully supported on Windows.
    if sys.platform == "win32":
        from rq.worker import SimpleWorker

        worker = SimpleWorker([queue], connection=redis_conn)
    else:
        from rq import Worker

        worker = Worker([queue], connection=redis_conn)

    worker.work()
