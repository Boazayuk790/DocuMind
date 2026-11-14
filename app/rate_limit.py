import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_hits = defaultdict(deque)
_lock = threading.Lock()


def rate_limit(name, limit, window_seconds):
    def dependency(request: Request):
        host = request.client.host if request.client else "unknown"
        key = (name, host)
        now = time.monotonic()

        with _lock:
            hits = _hits[key]

            while hits and now - hits[0] >= window_seconds:
                hits.popleft()

            if len(hits) >= limit:
                retry_after = int(window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)}
                )

            hits.append(now)

    return dependency


def reset():
    with _lock:
        _hits.clear()