import sys
import types

import pytest


@pytest.fixture(autouse=True)
def isolated_certificates(tmp_path, monkeypatch):
    """Never read or overwrite the user's real TLS identity during tests."""
    from padrelay.security import tls_utils

    directory = tmp_path / "certs"
    monkeypatch.setattr(tls_utils, "DEFAULT_CERT_DIR", directory)
    monkeypatch.setattr(tls_utils, "DEFAULT_CERT_FILE", directory / "server.crt")
    monkeypatch.setattr(tls_utils, "DEFAULT_KEY_FILE", directory / "server.key")


@pytest.fixture
def issued_certificate(tmp_path):
    """Issue real server certificates from a private test CA, including expired ones."""
    import ipaddress
    from datetime import datetime, timedelta, timezone

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "PadRelay test CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(True, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    ca_path = tmp_path / "test-ca.pem"
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))

    def issue(hostname="localhost", expired=False):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
        try:
            san = x509.IPAddress(ipaddress.ip_address(hostname))
        except ValueError:
            san = x509.DNSName(hostname)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(ca_name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=2))
            .not_valid_after(
                now - timedelta(days=1) if expired else now + timedelta(days=7)
            )
            .add_extension(x509.SubjectAlternativeName([san]), critical=False)
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None), critical=True
            )
            .add_extension(
                x509.KeyUsage(
                    True, False, True, False, False, False, False, False, False
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256())
        )
        cert_path, key_path = tmp_path / "issued.crt", tmp_path / "issued.key"
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        return cert_path, key_path, ca_path

    return issue


@pytest.fixture(autouse=True, scope="session")
def pygame_stub():
    if "pygame" not in sys.modules:
        joystick = types.SimpleNamespace(
            init=lambda: None,
            Joystick=lambda idx: types.SimpleNamespace(
                init=lambda: None,
                get_name=lambda: "dummy",
                get_numaxes=lambda: 0,
                get_numbuttons=lambda: 0,
                get_numhats=lambda: 0,
                get_button=lambda i: 0,
                get_axis=lambda i: 0.0,
                get_hat=lambda i: (0, 0),
            ),
            get_count=lambda: 0,
        )
        module = types.SimpleNamespace(
            init=lambda: None,
            quit=lambda: None,
            joystick=joystick,
            event=types.SimpleNamespace(pump=lambda: None),
        )
        sys.modules["pygame"] = module
    yield
