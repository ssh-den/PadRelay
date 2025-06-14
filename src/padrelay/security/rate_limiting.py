"""
Rate limiting utilities for the PadRelay
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import DefaultDict, Dict, Tuple
from ..core.logging_utils import get_logger
from ..server.constants import DEFAULT_BLOCK_DURATION

logger = get_logger(__name__)

class ConnectionTracker:
    """
    Track active connections and implement rate limiting
    """
    def __init__(
        self,
        max_connections: int = 1,
        rate_limit_window: int = 60,
        max_requests: int = 100,
        block_duration: int = DEFAULT_BLOCK_DURATION,
    ) -> None:
        """
        Initialize connection tracker
        
        Args:
            max_connections: Maximum number of simultaneous connections
            rate_limit_window: Time window for rate limiting in seconds
            max_requests: Maximum number of requests per window
        """
        self.clients: DefaultDict[Tuple[str, int], Dict] = defaultdict(lambda: {
            'last_seen': datetime.now(),
            'authenticated': False,
            'last_requests': []
        })
        self.max_connections = max_connections
        self.rate_limit_window = rate_limit_window
        self.max_requests = max_requests
        self.active_connections = 0
        self.block_duration = block_duration
        self.blocked_clients: Dict[Tuple[str, int], datetime] = {}

    def can_connect(self, addr: Tuple[str, int]) -> bool:
        """
        Check if a new connection is allowed
        
        Args:
            addr: Client address tuple
            
        Returns:
            bool: True if connection is allowed, False otherwise
        """
        self._cleanup()
        return self.active_connections < self.max_connections

    def is_rate_limited(self, addr: Tuple[str, int]) -> bool:
        """Check if client is being rate limited or blocked."""
        self._cleanup()
        now = datetime.now()

        # Check existing block
        if addr in self.blocked_clients:
            if now < self.blocked_clients[addr]:
                return True
            else:
                del self.blocked_clients[addr]

        client = self.clients[addr]

        # Remove expired requests
        client['last_requests'] = [t for t in client['last_requests']
                                   if now - t < timedelta(seconds=self.rate_limit_window)]

        # Add current request
        client['last_requests'].append(now)
        client['last_seen'] = now

        # Check if rate limit exceeded
        if len(client['last_requests']) > self.max_requests:
            self.blocked_clients[addr] = now + timedelta(seconds=self.block_duration)
            return True

        return False

    def is_blocked(self, addr: Tuple[str, int]) -> bool:
        """Check if a client is currently blocked"""
        self._cleanup()
        now = datetime.now()
        if addr in self.blocked_clients and now < self.blocked_clients[addr]:
            return True
        return False

    def authenticate(self, addr: Tuple[str, int]) -> None:
        """
        Mark a client as authenticated
        
        Args:
            addr: Client address tuple
        """
        if not self.clients[addr]['authenticated']:
            self.active_connections += 1
            
        self.clients[addr]['authenticated'] = True
        self.clients[addr]['last_seen'] = datetime.now()
        logger.info(f"Client {addr} authenticated. Active connections: {self.active_connections}")

    def disconnect(self, addr: Tuple[str, int]) -> None:
        """
        Handle client disconnection
        
        Args:
            addr: Client address tuple
        """
        if addr in self.clients and self.clients[addr]['authenticated']:
            self.active_connections -= 1
            self.clients[addr]['authenticated'] = False
            logger.info(f"Client {addr} disconnected. Active connections: {self.active_connections}")

    def _cleanup(self) -> None:
        """Clean up expired client and block records"""
        now = datetime.now()
        expired = [addr for addr, data in self.clients.items()
                   if now - data['last_seen'] > timedelta(minutes=5)]

        for addr in expired:
            if self.clients[addr]['authenticated']:
                self.active_connections -= 1
            del self.clients[addr]

        expired_blocks = [addr for addr, expiry in self.blocked_clients.items()
                          if now > expiry]
        for addr in expired_blocks:
            del self.blocked_clients[addr]
