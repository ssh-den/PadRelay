import argparse
import sys

import pytest

from padrelay.core import config


def test_load_config_and_validate(tmp_path):
    cfg_content = """
[server]
host=127.0.0.1
port=1234
password=test
protocol=tcp
[vgamepad]
type=ds4
"""
    cfg_file = tmp_path / "cfg.ini"
    cfg_file.write_text(cfg_content)

    cfg = config.load_config(str(cfg_file))
    assert cfg.get("server", "host") == "127.0.0.1"

    args = argparse.Namespace(
        host="1.2.3.4",
        port=8000,
        password="pw",
        gamepad_type="xbox360",
        protocol="tcp",
        block_duration=1,
    )
    # Should not raise
    config.validate_server_config(args, cfg)


def test_validate_server_config_errors():
    args = argparse.Namespace(
        host="",
        port=70000,
        password=None,
        gamepad_type="bad",
        protocol="tcp",
        block_duration=0,
    )
    with pytest.raises(ValueError):
        config.validate_server_config(args, None)


def test_parse_client_args_defaults(monkeypatch):
    monkeypatch.setattr(config.getpass, "getpass", lambda _: "pw")
    monkeypatch.setattr(sys, "argv", ["prog"])

    args, cfg_obj = config.parse_client_args()

    assert args.server_ip == "127.0.0.1"
    assert args.server_port == 9999
    assert args.protocol == "tcp"
    assert args.joystick_index == 0
    assert args.update_rate == 60
    assert args.password == "pw"
    assert cfg_obj is None


def test_parse_client_args_config_and_override(tmp_path, monkeypatch):
    cfg = tmp_path / "c.ini"
    cfg.write_text("""[network]
server_ip=10.0.0.1
server_port=1111
protocol=udp
password=config_pw
[joystick]
index=2
[client]
update_rate=30
""")

    def not_called(_):
        raise AssertionError("prompt called")

    monkeypatch.setattr(config.getpass, "getpass", not_called)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--config",
            str(cfg),
            "--server-ip",
            "1.2.3.4",
            "--password",
            "cli_pw",
        ],
    )

    args, cfg_obj = config.parse_client_args()

    assert cfg_obj is not None
    assert args.server_ip == "1.2.3.4"  # CLI overrides config
    assert args.server_port == 1111
    assert args.protocol == "udp"
    assert args.joystick_index == 2
    assert args.update_rate == 30
    assert args.password == "cli_pw"


def test_parse_server_args_defaults(monkeypatch):
    monkeypatch.setattr(config.getpass, "getpass", lambda _: "pw")
    monkeypatch.setattr(sys, "argv", ["prog"])

    args, cfg_obj = config.parse_server_args()

    assert args.host == "127.0.0.1"
    assert args.port == 9999
    assert args.gamepad_type == "xbox360"
    assert args.protocol == "tcp"
    assert args.rate_limit_window == config.DEFAULT_RATE_LIMIT_WINDOW
    assert args.max_requests == config.DEFAULT_MAX_REQUESTS
    assert args.block_duration == config.DEFAULT_BLOCK_DURATION
    assert args.password == "pw"
    assert cfg_obj is None


def test_parse_server_args_config_and_override(tmp_path, monkeypatch):
    cfg = tmp_path / "s.ini"
    cfg.write_text("""[server]
host=127.0.0.1
port=4321
protocol=udp
password=config_pw
rate_limit_window=5
max_requests=10
block_duration=4
[vgamepad]
type=ds4
""")

    def not_called(_):
        raise AssertionError("prompt called")

    monkeypatch.setattr(config.getpass, "getpass", not_called)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--config",
            str(cfg),
            "--protocol",
            "tcp",
            "--max-requests",
            "20",
        ],
    )

    args, cfg_obj = config.parse_server_args()

    assert cfg_obj is not None
    assert args.host == "127.0.0.1"
    assert args.port == 4321
    assert args.protocol == "tcp"  # CLI override
    assert args.gamepad_type == "ds4"
    assert args.password.startswith("pbkdf2_sha256$")
    assert args.rate_limit_window == 5
    assert args.max_requests == 20
    assert args.block_duration == 4


def test_parse_server_args_udp_defaults(monkeypatch):
    def not_called(_):
        raise AssertionError("prompt called")

    monkeypatch.setattr(config.getpass, "getpass", not_called)
    monkeypatch.setattr(sys, "argv", ["prog", "--protocol", "udp"])

    args, cfg_obj = config.parse_server_args()

    assert args.protocol == "udp"
    assert args.max_requests == config.DEFAULT_UDP_MAX_REQUESTS
    assert args.password is None
    assert cfg_obj is None


def test_env_password_override(monkeypatch, tmp_path):
    cfg = tmp_path / "s.ini"
    cfg.write_text("[server]\nport=1234\npassword=cfg_pw\n")
    monkeypatch.setenv("PASSWORD", "env_pw")
    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(cfg)])

    args, cfg_obj = config.parse_server_args()

    assert args.password == "env_pw"


def test_password_hashing_for_udp(tmp_path, monkeypatch):
    cfg = tmp_path / "s.ini"
    cfg.write_text("[server]\nprotocol=udp\npassword=pw\n")
    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(cfg)])

    args, cfg_obj = config.parse_server_args()

    assert args.password.startswith("pbkdf2_sha256$")
    assert cfg_obj is not None
    assert cfg_obj["server"]["password"].startswith("pbkdf2_sha256$")


def test_client_password_hash_env(monkeypatch):
    hashed = "pbkdf2_sha256$1$abc$def"
    monkeypatch.setenv("PASSWORD_HASH", hashed)
    monkeypatch.setattr(
        config.getpass,
        "getpass",
        lambda _: (_ for _ in ()).throw(AssertionError("prompt")),
    )
    monkeypatch.setattr(sys, "argv", ["prog", "--protocol", "udp"])

    args, cfg_obj = config.parse_client_args()

    assert args.password == hashed
    assert cfg_obj is None


@pytest.mark.parametrize("override", [False, True])
def test_client_tls_trust_configuration(monkeypatch, tmp_path, override):
    path = tmp_path / "client.ini"
    path.write_text(
        "[network]\nprotocol=tcp\npassword=test-password\n"
        "[security]\nenable_tls=true\nca_path=config.pem\nserver_hostname=config.test\n"
    )
    argv = ["padrelay-client", "--config", str(path)]
    if override:
        argv += ["--ca-path", "cli.pem", "--server-hostname", "cli.test"]
    monkeypatch.setattr(sys, "argv", argv)
    args, _ = config.parse_client_args()
    assert args.enable_tls
    assert args.ca_path == ("cli.pem" if override else "config.pem")
    assert args.server_hostname == ("cli.test" if override else "config.test")


@pytest.mark.parametrize("stored_password", ["config-password", ""])
def test_server_cli_password_is_not_replaced_by_ini_migration(
    monkeypatch, tmp_path, stored_password
):
    path = tmp_path / "server.ini"
    original = f"[server]\npassword={stored_password}\n"
    path.write_text(original)
    monkeypatch.setattr(
        sys, "argv", ["prog", "--config", str(path), "--password", "cli-password"]
    )
    args, _ = config.parse_server_args()
    assert args.password == "cli-password"
    assert path.read_text() == original


def test_server_config_without_server_section(monkeypatch, tmp_path):
    path = tmp_path / "server.ini"
    path.write_text("[security]\nenable_tls=true\n")
    monkeypatch.setattr(
        sys, "argv", ["prog", "--config", str(path), "--password", "cli-password"]
    )
    args, _ = config.parse_server_args()
    assert args.password == "cli-password"


def test_empty_ini_password_cannot_become_valid_udp_credential(monkeypatch, tmp_path):
    path = tmp_path / "server.ini"
    original = "[server]\nprotocol=udp\npassword=\n"
    path.write_text(original)
    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(path)])
    args, cfg = config.parse_server_args()
    with pytest.raises(ValueError, match="Password is required"):
        config.validate_server_config(args, cfg)
    assert path.read_text() == original
