"""Minimal per-IP sliding-window rate limiter.

In-memory, so it only limits correctly within a single process. That's a
deliberate scope cut for now — this app is meant to run as one persistent
server (see README), not horizontally scaled. If it ever runs as multiple
instances behind a load balancer, this needs to move to a shared store
(e.g. Redis) or every instance enforces its own separate quota.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.config import get_settings


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_s: float) -> None:
        self.max_requests = max_requests
        self.window_s = window_s
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.monotonic()
        window_start = now - self.window_s
        hits = self._hits[key]
        # Drop timestamps outside the window.
        while hits and hits[0] < window_start:
            hits.pop(0)

        if len(hits) >= self.max_requests:
            retry_after = int(hits[0] + self.window_s - now) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded: max {self.max_requests} research "
                    f"queries per {int(self.window_s)}s per client. "
                    f"Retry in {retry_after}s."
                ),
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)


_limiter: SlidingWindowRateLimiter | None = None


def _get_limiter() -> SlidingWindowRateLimiter:
    global _limiter
    if _limiter is None:
        settings = get_settings()
        _limiter = SlidingWindowRateLimiter(
            max_requests=settings.rate_limit_max_requests,
            window_s=settings.rate_limit_window_s,
        )
    return _limiter


def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency: raises 429 if this client is over quota."""
    client_ip = request.client.host if request.client else "unknown"
    _get_limiter().check(client_ip)
