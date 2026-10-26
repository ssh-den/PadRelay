#!/usr/bin/env python3
"""
Entry point for the PadRelay client
"""
import asyncio
import signal
import sys

from padrelay.core.config import parse_client_args
from padrelay.core.logging_utils import get_logger
from padrelay.client.client_app import VirtualGamepadClient
from padrelay.client.input import GamepadInput

logger = get_logger("client")

async def async_main():

    # Parse command line arguments
    args, config_obj = parse_client_args()
    
    # Initialize gamepad input
    gamepad = GamepadInput(args.joystick_index)
    if not gamepad.initialize():
        logger.error("Failed to initialize gamepad. Exiting.")
        return 1
    
    # Create client application
    client = VirtualGamepadClient(
        server_ip=args.server_ip,
        server_port=args.server_port,
        protocol=args.protocol,
        gamepad=gamepad,
        update_rate=args.update_rate,
        password=args.password,
        config=config_obj,
        enable_tls=args.enable_tls,
    )
    
    # Set up signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda: asyncio.create_task(client.shutdown())
        )
    
    # Run the client
    try:
        await client.run()
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return 1

def main():
   
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Client terminated by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
