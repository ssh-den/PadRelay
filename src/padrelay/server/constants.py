"""Constants used by the server"""

# Maximum number of simultaneous connections
MAX_CONNECTIONS = 1

# Default rate limit window in seconds
DEFAULT_RATE_LIMIT_WINDOW = 60

# Default maximum requests per window
DEFAULT_MAX_REQUESTS = 100

# Default maximum requests per window when using UDP
DEFAULT_UDP_MAX_REQUESTS = 6000

# Default duration to block clients that exceed the rate limit (seconds)
DEFAULT_BLOCK_DURATION = 2

# Default host to bind to
DEFAULT_HOST = "127.0.0.1"
