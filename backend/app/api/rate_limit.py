"""Fixed-window rate limiter driven by the injected clock, so limits are testable."""

from __future__ import annotations

import threading
from collections import defaultdict

from app.core.clock import Clock
from app.core.errors import RateLimited


class RateLimiter:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._counts: dict[tuple[str, str, int], int] = defaultdict(int)
        self._lock = threading.Lock()

    def hit(self, scope: str, key: str, *, limit: int, window_seconds: int) -> None:
        """Count one request. Raises RateLimited once `limit` is exceeded in the window."""
        window = int(self._clock.now().timestamp()) // window_seconds
        with self._lock:
            bucket = (scope, key, window)
            self._counts[bucket] += 1
            if self._counts[bucket] > limit:
                raise RateLimited()
