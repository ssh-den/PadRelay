import asyncio
import json
import pytest

from padrelay.protocol.tcp import TCPProtocolHandler


@pytest.mark.asyncio
async def test_tcp_handler_send_and_receive():
    async def echo(reader, writer):
        handler = TCPProtocolHandler(reader, writer)
        msg = await handler.read_message()
        await handler.send_message(msg)
        await handler.drain()
        writer.close()

    server = await asyncio.start_server(echo, "127.0.0.1", 0)
    addr = server.sockets[0].getsockname()

    reader, writer = await asyncio.open_connection(*addr)
    handler = TCPProtocolHandler(reader, writer)
    test_msg = {"type": "test", "value": 1}
    assert await handler.send_message(test_msg)
    await handler.drain()
    received = await handler.read_message()
    assert received == test_msg
    writer.close()
    await writer.wait_closed()
    server.close()
    await server.wait_closed()
