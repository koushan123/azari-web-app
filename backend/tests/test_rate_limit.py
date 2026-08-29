from backend.app.core.rate_limit import InMemoryRateLimiter


def test_rate_limit_resets_after_sliding_window() -> None:
    current_time = 100.0

    def clock() -> float:
        return current_time

    limiter = InMemoryRateLimiter(limit=2, window_seconds=10, clock=clock)
    assert limiter.check("login:127.0.0.1") is None
    assert limiter.check("login:127.0.0.1") is None
    assert limiter.check("login:127.0.0.1") == 10

    current_time += 10
    assert limiter.check("login:127.0.0.1") is None
