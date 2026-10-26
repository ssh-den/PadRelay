import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from padrelay.scripts import client as client_script
from padrelay.scripts import server as server_script


def test_padrelay_client_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["padrelay-client", "--help"])
    with pytest.raises(SystemExit) as exc:
        client_script.main()
    out = capsys.readouterr().out
    assert "PadRelay Client" in out
    assert exc.value.code == 0


def test_padrelay_server_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["padrelay-server", "--help"])
    with pytest.raises(SystemExit) as exc:
        server_script.main()
    out = capsys.readouterr().out
    assert "PadRelay Server" in out
    assert exc.value.code == 0


def test_client_missing_config(monkeypatch, caplog):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "padrelay-client",
            "--config",
            "nope.ini",
            "--password",
            "pw",
        ],
    )
    with caplog.at_level(logging.ERROR):
        ret = client_script.main()
    assert ret == 1
    assert any("Error loading configuration" in rec.message for rec in caplog.records)


def test_client_cli_passes_tls_trust_to_application(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "padrelay-client",
            "--password",
            "test-password",
            "--ca-path",
            "trusted.pem",
            "--server-hostname",
            "padrelay.test",
        ],
    )
    monkeypatch.setattr(client_script, "GamepadInput", Mock())
    constructor = Mock(side_effect=ValueError("stop before starting application"))
    monkeypatch.setattr(client_script, "VirtualGamepadClient", constructor)
    assert client_script.main() == 1
    assert constructor.call_args.kwargs["enable_tls"] is True
    assert constructor.call_args.kwargs["ca_path"] == Path("trusted.pem")
    assert constructor.call_args.kwargs["server_hostname"] == "padrelay.test"


@pytest.mark.asyncio
@pytest.mark.parametrize("success", [False, True])
async def test_client_cli_supports_windows_signals_and_preserves_exit_status(
    monkeypatch, success
):
    monkeypatch.setattr(sys, "argv", ["padrelay-client", "--password", "test-password"])
    monkeypatch.setattr(client_script, "GamepadInput", Mock())
    application = Mock(run=AsyncMock(return_value=success), shutdown=AsyncMock())
    monkeypatch.setattr(
        client_script, "VirtualGamepadClient", Mock(return_value=application)
    )
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(
        loop, "add_signal_handler", Mock(side_effect=NotImplementedError)
    )
    register = Mock()
    monkeypatch.setattr(client_script.signal, "signal", register)

    assert await client_script.async_main() == (0 if success else 1)
    assert register.call_count == 2
    callback = register.call_args.args[1]
    callback(None, None)
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    application.shutdown.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("success", [False, True])
async def test_server_cli_preserves_application_exit_status(monkeypatch, success):
    monkeypatch.setattr(sys, "argv", ["padrelay-server", "--password", "test-password"])
    application = Mock(run=AsyncMock(return_value=success))
    monkeypatch.setattr(
        server_script, "VirtualGamepadServer", Mock(return_value=application)
    )
    monkeypatch.setattr(asyncio.get_running_loop(), "add_signal_handler", Mock())
    monkeypatch.setattr(server_script.threading, "Thread", Mock())
    assert await server_script.async_main() == (0 if success else 1)
