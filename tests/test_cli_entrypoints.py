import sys
import logging
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
    monkeypatch.setattr(sys, "argv", [
        "padrelay-client",
        "--config",
        "nope.ini",
        "--password",
        "pw",
    ])
    with caplog.at_level(logging.ERROR):
        ret = client_script.main()
    assert ret == 1
    assert any("Error loading configuration" in rec.message for rec in caplog.records)
