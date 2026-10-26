from padrelay.client import client_app
from padrelay.client import input as client_input
from padrelay.core import config
from padrelay.protocol import tcp, udp
from padrelay.security import auth, rate_limiting
from padrelay.server import input_processor, server_app, virtual_gamepad


def test_functions_exist():
    # Core config functions
    assert hasattr(config, "load_config")
    assert hasattr(config, "parse_client_args")
    assert hasattr(config, "parse_server_args")

    # Client methods
    assert hasattr(client_input.GamepadInput, "initialize")
    assert hasattr(client_input.GamepadInput, "poll")
    assert hasattr(client_app.VirtualGamepadClient, "_tcp_auth")
    assert hasattr(client_app.VirtualGamepadClient, "_tcp_heartbeat_loop")
    assert hasattr(client_app.VirtualGamepadClient, "_run_tcp")
    assert hasattr(client_app.VirtualGamepadClient, "_run_udp")

    # Protocol handlers
    assert hasattr(tcp.TCPProtocolHandler, "read_message")
    assert hasattr(tcp.TCPProtocolHandler, "send_message")
    assert hasattr(udp.UDPServerProtocol, "datagram_received")

    # Security
    assert hasattr(rate_limiting.ConnectionTracker, "can_connect")
    assert hasattr(rate_limiting.ConnectionTracker, "is_rate_limited")
    assert hasattr(auth.Authenticator, "generate_tcp_response")

    # Server
    assert hasattr(server_app.VirtualGamepadServer, "_handle_tcp_client")
    assert hasattr(server_app.VirtualGamepadServer, "_run_udp_server")
    assert hasattr(input_processor.GamepadHandler, "process")
    assert hasattr(virtual_gamepad.VirtualGamepad, "load_button_mapping")
