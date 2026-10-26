#!/usr/bin/env python3
"""
Entry point for the PadRelay server
"""
import asyncio
import signal
import sys
import threading

from padrelay.core.config import parse_server_args, validate_server_config
from padrelay.core.logging_utils import get_logger
from padrelay.server.server_app import VirtualGamepadServer
from padrelay.core.exceptions import ConfigurationError

logger = get_logger("server")

async def async_main():

    # Parse command line arguments
    args, config_obj = parse_server_args()
    
    # Validate configuration
    try:
        validate_server_config(args, config_obj)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    
    # Create server application
    from pathlib import Path
    server = VirtualGamepadServer(
        host=args.host,
        port=args.port,
        password=args.password,
        gamepad_type=args.gamepad_type,
        config=config_obj,
        rate_limit_window=args.rate_limit_window,
        max_requests=args.max_requests,
        block_duration=args.block_duration,
        protocol=args.protocol,
        enable_tls=args.enable_tls,
        cert_path=Path(args.cert_path) if args.cert_path else None,
        key_path=Path(args.key_path) if args.key_path else None,
    )
    
    # Set up signal handlers for clean shutdown
    loop = asyncio.get_running_loop()

    # Create a threading Event for Windows signal handling
    stop_event = threading.Event()

    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(server.shutdown()))
        except NotImplementedError:
            # Fallback for Windows where add_signal_handler isn't supported
            signal.signal(sig, lambda s, f: stop_event.set())

    # Start the monitoring thread for Windows compatibility
    def signal_monitor():
        # Block until signal is received or stop_event is set
        stop_event.wait()
        # Try to stop the event loop if not already stopped
        loop.call_soon_threadsafe(lambda: asyncio.create_task(server.shutdown()))

    monitor_thread = threading.Thread(target=signal_monitor, daemon=True)
    monitor_thread.start()
    
    # Run the server
    try:
        await server.run()
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return 1

def main():

    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Server terminated by user")
        return 0
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
