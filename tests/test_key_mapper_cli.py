import sys

import pytest

from padrelay.scripts import key_mapper as key_mapper_script


def test_padrelay_keymapper_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["padrelay-keymapper", "--help"])
    with pytest.raises(SystemExit) as exc:
        key_mapper_script.main()
    out = capsys.readouterr().out
    assert "--joystick-index" in out and "--output" in out
    assert exc.value.code == 0
