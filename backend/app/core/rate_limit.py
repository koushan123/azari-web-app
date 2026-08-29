from collections import defaultdict, deque
from collections.abc import Callable
from math import ceil
from threading import Lock
from time import monotonic


class InMemoryRateLimiter:
    """A process-local sliding-window limiter for a small single-instance deployment."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> int | None:
        """Record an attempt, returning retry seconds when the key is limited."""
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= self.limit:
                return max(1, ceil(attempts[0] + self.window_seconds - now))
            attempts.append(now)
            return None

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()
