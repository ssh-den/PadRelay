from datetime import timedelta, datetime
from padrelay.security.rate_limiting import ConnectionTracker


def test_connection_tracker_basic():
    tracker = ConnectionTracker(max_connections=2, rate_limit_window=1, max_requests=5)
    addr = ("127.0.0.1", 12345)

    assert tracker.can_connect(addr)
    tracker.authenticate(addr)
    assert tracker.active_connections == 1

    for _ in range(5):
        assert not tracker.is_rate_limited(addr)
    # next request should exceed limit
    assert tracker.is_rate_limited(addr)

    tracker.disconnect(addr)
    assert tracker.active_connections == 0
