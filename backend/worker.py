import os
import sys

# RQ's scheduler.py calls get_context('fork') at import time.
# Windows doesn't support 'fork' so we intercept the call and redirect to 'spawn'.
if sys.platform == "win32":
    import multiprocessing
    import multiprocessing.context

    _original_get_context = multiprocessing.context.BaseContext.get_context

    def _patched_get_context(self, method=None):
        if method == "fork":
            method = "spawn"
        return _original_get_context(self, method)

    multiprocessing.context.BaseContext.get_context = _patched_get_context

from redis import Redis
from rq import Queue
from storage import init_bucket

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_conn = Redis(host=redis_host, port=6379)

if __name__ == "__main__":
    try:
        init_bucket()
    except Exception as e:
        print(f"[Worker] Failed to init S3 bucket: {e}", file=sys.stderr)
        sys.exit(1)

    # Queue defined here only to pass to the worker
    queue = Queue(connection=redis_conn)

    if sys.platform == "win32":
        from rq.worker import SimpleWorker

        worker = SimpleWorker([queue], connection=redis_conn)
    else:
        from rq import Worker

        worker = Worker([queue], connection=redis_conn)

    worker.work()
