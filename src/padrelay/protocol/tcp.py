"""TCP protocol utilities for the PadRelay"""
import asyncio
import json
import struct
from ..core.logging_utils import get_logger
from .constants import MAX_MESSAGE_SIZE

logger = get_logger(__name__)

class TCPProtocolHandler:
    """Handle TCP communication"""
    
    def __init__(self, reader=None, writer=None):
        """Initialize with optional reader/writer"""
        self.reader = reader
        self.writer = writer
    
    async def read_message(self):
        """Read and decode a length-prefixed message"""
        try:
            # Read 4-byte length prefix
            header = await self.reader.readexactly(4)
            msg_length = struct.unpack('>I', header)[0]
            
            if msg_length > MAX_MESSAGE_SIZE:
                logger.warning(f"Message too large: {msg_length} bytes")
                raise ValueError("Message too large")
                
            # Read the message data
            data = await self.reader.readexactly(msg_length)
            return json.loads(data.decode('utf-8'))
        except asyncio.IncompleteReadError:
            # Connection closed
            logger.debug("Connection closed")
            return None
        except (json.JSONDecodeError, struct.error) as e:
            logger.error(f"Error decoding message: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading message: {e}")
            return None

    async def send_message(self, message):
        """Send a length-prefixed message"""
        try:
            if isinstance(message, dict):
                data = json.dumps(message).encode('utf-8')
            elif isinstance(message, str):
                data = message.encode('utf-8')
            else:
                data = message
                
            self.writer.write(struct.pack('>I', len(data)) + data)
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def drain(self):
        """Flush the writer buffer"""
        try:
            await self.writer.drain()
            return True
        except Exception as e:
            logger.error(f"Error draining writer: {e}")
            return False
    
    def close(self):
        """Close the writer connection"""
        if self.writer:
            try:
                self.writer.close()
            except Exception as e:
                logger.error(f"Error closing writer: {e}")
    
    async def wait_closed(self) -> None:
        """Wait for the writer to close"""
        if self.writer:
            try:
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"Error waiting for writer to close: {e}")
