"""TLS setup rejects invalid trust files and incomplete or invalid server identities."""

import ssl
from unittest.mock import Mock

import pytest

from padrelay.client import client_app
from padrelay.security import tls_utils
from padrelay.server import server_app


def test_client_verifies_server_identity_by_default():
    client = client_app.VirtualGamepadClient(
        "localhost", 9999, "tcp", Mock(), enable_tls=True
    )
    assert client.ssl_context.verify_mode == ssl.CERT_REQUIRED
    assert client.ssl_context.check_hostname


def test_client_context_verifies_by_default():
    context = tls_utils.create_client_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname


def test_missing_ca_does_not_disable_verification(tmp_path):
    with pytest.raises(FileNotFoundError):
        tls_utils.create_client_ssl_context(
            verify_cert=True, ca_path=tmp_path / "missing.pem"
        )


def test_client_tls_initialization_failure_aborts(monkeypatch):
    def fail(**kwargs):
        raise ssl.SSLError("TLS initialization failed")

    monkeypatch.setattr(client_app, "create_client_ssl_context", fail)
    with pytest.raises(ssl.SSLError):
        client_app.VirtualGamepadClient(
            "localhost", 9999, "tcp", Mock(), enable_tls=True
        )


@pytest.mark.parametrize(
    "error",
    [
        ssl.SSLError("invalid certificate"),
        ImportError("cryptography unavailable"),
        OSError("key unreadable"),
    ],
)
def test_server_tls_initialization_failure_aborts(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(server_app, "VirtualGamepad", Mock())
    monkeypatch.setattr(server_app, "create_server_ssl_context", fail)
    with pytest.raises(type(error)):
        server_app.VirtualGamepadServer(
            "127.0.0.1", 0, "test-password", enable_tls=True
        )


def test_missing_custom_certificate_is_not_generated(monkeypatch, tmp_path):
    monkeypatch.setattr(server_app, "VirtualGamepad", Mock())
    cert, key = tmp_path / "missing.crt", tmp_path / "missing.key"
    with pytest.raises(FileNotFoundError):
        server_app.VirtualGamepadServer(
            "127.0.0.1",
            0,
            "test-password",
            enable_tls=True,
            cert_path=cert,
            key_path=key,
        )
    assert not cert.exists() and not key.exists()


def test_partial_identity_is_not_overwritten(tmp_path):
    cert, key = tmp_path / "existing.crt", tmp_path / "missing.key"
    cert.write_bytes(b"keep the existing certificate")
    with pytest.raises(FileNotFoundError):
        tls_utils.create_server_ssl_context(cert, key, auto_generate=True)
    assert cert.read_bytes() == b"keep the existing certificate"
    assert not key.exists()


def test_custom_certificate_requires_key(monkeypatch, tmp_path):
    monkeypatch.setattr(server_app, "VirtualGamepad", Mock())
    with pytest.raises(ValueError):
        server_app.VirtualGamepadServer(
            "127.0.0.1",
            0,
            "test-password",
            enable_tls=True,
            cert_path=tmp_path / "server.crt",
        )


def test_malformed_ca_aborts_client(tmp_path):
    ca = tmp_path / "invalid.pem"
    ca.write_text("not a certificate")
    with pytest.raises(ssl.SSLError):
        client_app.VirtualGamepadClient(
            "localhost", 9999, "tcp", Mock(), enable_tls=True, ca_path=ca
        )


@pytest.mark.parametrize("invalid", ["malformed", "mismatched-key"])
def test_invalid_identity_aborts_server(monkeypatch, tmp_path, invalid):
    monkeypatch.setattr(server_app, "VirtualGamepad", Mock())
    cert, key = tls_utils.generate_self_signed_cert(
        tmp_path / "server.crt", tmp_path / "server.key"
    )
    if invalid == "malformed":
        cert.write_text("not a certificate")
    else:
        _, key = tls_utils.generate_self_signed_cert(
            tmp_path / "other.crt", tmp_path / "other.key"
        )
    with pytest.raises(ssl.SSLError):
        server_app.VirtualGamepadServer(
            "127.0.0.1",
            0,
            "test-password",
            enable_tls=True,
            cert_path=cert,
            key_path=key,
        )
