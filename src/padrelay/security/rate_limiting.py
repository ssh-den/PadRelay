"""Bounded IP/global token buckets and atomic connection reservations."""

import time
from dataclasses import dataclass

from ..server.constants import DEFAULT_BLOCK_DURATION


@dataclass
class _Bucket:
    tokens: float
    updated: float
    blocked_until: float = 0


class ConnectionTracker:
    """Admission operations run synchronously on the server event loop."""

    def __init__(
        self,
        max_connections: int = 1,
        rate_limit_window: int = 60,
        max_requests: int = 100,
        block_duration: int = DEFAULT_BLOCK_DURATION,
        max_tracked_ips: int = 1024,
        global_max_requests: int = 12000,
    ) -> None:
        if (
            min(
                max_connections,
                rate_limit_window,
                max_requests,
                block_duration,
                max_tracked_ips,
                global_max_requests,
            )
            <= 0
        ):
            raise ValueError("Admission limits must be positive")
        self.max_connections = max_connections
        self.rate_limit_window = rate_limit_window
        self.max_requests = max_requests
        self.block_duration = block_duration
        self.max_tracked_ips = max_tracked_ips
        self.global_max_requests = global_max_requests
        self.clients: dict[str, _Bucket] = {}
        self._pending: set[tuple] = set()
        self._authenticated: set[tuple] = set()
        self._global = _Bucket(float(global_max_requests), time.monotonic())
        self._last_cleanup = time.monotonic()

    @property
    def active_connections(self) -> int:
        return len(self._authenticated)

    @property
    def pending_connections(self) -> int:
        return len(self._pending)

    def can_connect(self, addr: tuple) -> bool:
        return addr not in self._pending | self._authenticated and (
            self.active_connections + self.pending_connections < self.max_connections
        )

    def reserve(self, addr: tuple) -> bool:
        """Claim a connection slot synchronously before network waits."""
        if not self.can_connect(addr):
            return False
        self._pending.add(addr)
        return True

    def authenticate(self, addr: tuple) -> None:
        if addr in self._authenticated:
            return
        if addr not in self._pending and not self.reserve(addr):
            raise ValueError("No connection reservation available")
        self._pending.discard(addr)
        self._authenticated.add(addr)

    def disconnect(self, addr: tuple) -> None:
        self._pending.discard(addr)
        self._authenticated.discard(addr)

    def _take(self, bucket: _Bucket, capacity: int, now: float) -> bool:
        bucket.tokens = min(
            capacity,
            bucket.tokens + (now - bucket.updated) * capacity / self.rate_limit_window,
        )
        bucket.updated = now
        if now < bucket.blocked_until:
            return False
        if bucket.tokens < 1:
            bucket.blocked_until = now + self.block_duration
            return False
        bucket.tokens -= 1
        return True

    def is_rate_limited(self, addr: tuple) -> bool:
        now = time.monotonic()
        # Check the global packet budget before allocating a per-IP bucket.
        if not self._take(self._global, self.global_max_requests, now):
            return True
        if now - self._last_cleanup >= 1:
            self._cleanup(now)
        ip = addr[0]
        bucket = self.clients.get(ip)
        if bucket is None:
            # Fail closed at capacity: new IPs cannot evict existing blocks.
            if len(self.clients) >= self.max_tracked_ips:
                return True
            bucket = self.clients[ip] = _Bucket(float(self.max_requests), now)
        return not self._take(bucket, self.max_requests, now)

    def is_blocked(self, addr: tuple) -> bool:
        bucket = self.clients.get(addr[0])
        return bucket is not None and time.monotonic() < bucket.blocked_until

    def _cleanup(self, now: float) -> None:
        self._last_cleanup = now
        ttl = max(self.rate_limit_window, self.block_duration)
        for ip, bucket in list(self.clients.items()):
            if now - bucket.updated >= ttl and now >= bucket.blocked_until:
                del self.clients[ip]
