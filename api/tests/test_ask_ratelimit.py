from empu.ask.ratelimit import RateLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allows_up_to_the_limit():
    limiter = RateLimiter(max_events=3, window_s=60, clock=Clock())
    assert [limiter.allow("ip") for _ in range(3)] == [True, True, True]


def test_blocks_over_the_limit():
    limiter = RateLimiter(max_events=2, window_s=60, clock=Clock())
    limiter.allow("ip")
    limiter.allow("ip")
    assert limiter.allow("ip") is False


def test_window_slides_and_frees_slots():
    clock = Clock()
    limiter = RateLimiter(max_events=2, window_s=60, clock=clock)
    limiter.allow("ip")
    limiter.allow("ip")
    assert limiter.allow("ip") is False

    clock.advance(61)

    assert limiter.allow("ip") is True


def test_keys_are_independent():
    limiter = RateLimiter(max_events=1, window_s=60, clock=Clock())
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    assert limiter.allow("b") is True
