"""TLS/SSL utilities for secure communication"""

import ipaddress
import os
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from ..core.logging_utils import get_logger

logger = get_logger(__name__)

# Default certificate paths
DEFAULT_CERT_DIR = Path.home() / ".padrelay" / "certs"
DEFAULT_CERT_FILE = DEFAULT_CERT_DIR / "server.crt"
DEFAULT_KEY_FILE = DEFAULT_CERT_DIR / "server.key"


def get_default_cert_paths() -> Tuple[Path, Path]:
    """Get default paths for certificate and key files

    Returns:
        Tuple of (cert_path, key_path)
    """
    return DEFAULT_CERT_FILE, DEFAULT_KEY_FILE


def ensure_cert_dir_exists() -> Path:
    """Ensure certificate directory exists with proper permissions

    Returns:
        Path to certificate directory
    """
    DEFAULT_CERT_DIR.mkdir(parents=True, exist_ok=True)
    # Set directory permissions to owner-only (700)
    os.chmod(DEFAULT_CERT_DIR, 0o700)
    return DEFAULT_CERT_DIR


def generate_self_signed_cert(
    cert_path: Optional[Path] = None,
    key_path: Optional[Path] = None,
    days_valid: int = 365,
    country: str = "US",
    state: str = "State",
    locality: str = "City",
    organization: str = "PadRelay",
    common_name: str = "localhost",
) -> Tuple[Path, Path]:
    """Generate a self-signed certificate for TLS

    Args:
        cert_path: Path where certificate will be saved (default: ~/.padrelay/certs/server.crt)
        key_path: Path where private key will be saved (default: ~/.padrelay/certs/server.key)
        days_valid: Number of days the certificate is valid (default: 365)
        country: Country code for certificate (default: US)
        state: State/Province for certificate
        locality: City for certificate
        organization: Organization name for certificate
        common_name: Common name (hostname) for certificate

    Returns:
        Tuple of (cert_path, key_path)
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        logger.error(
            "cryptography package not installed. "
            "Install with: pip install cryptography"
        )
        raise

    # Use default paths if not provided
    if cert_path is None:
        cert_path = DEFAULT_CERT_FILE
    if key_path is None:
        key_path = DEFAULT_KEY_FILE

    # Only change permissions on our own directory, never a supplied parent.
    if cert_path.parent == DEFAULT_CERT_DIR or key_path.parent == DEFAULT_CERT_DIR:
        ensure_cert_dir_exists()
    cert_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    logger.info("Generating self-signed certificate...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create certificate subject and issuer (same for self-signed)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
            x509.NameAttribute(NameOID.LOCALITY_NAME, locality),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    names: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]
    name: x509.GeneralName
    if common_name != "localhost":
        try:
            name = x509.IPAddress(ipaddress.ip_address(common_name))
        except ValueError:
            name = x509.DNSName(common_name)
        if name not in names:
            names.append(name)

    # Build certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=days_valid))
        .add_extension(
            x509.SubjectAlternativeName(names),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Create with restrictive permissions before writing any key material.
    # Exclusive creation also refuses existing files and symlinks.
    if cert_path.exists() or key_path.exists():
        raise FileExistsError("Refusing to replace an existing TLS identity")
    with os.fdopen(
        os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
    ) as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Write certificate to file
    with os.fdopen(
        os.open(cert_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
    ) as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    logger.info(f"Certificate generated: {cert_path}")
    logger.info(f"Private key generated: {key_path}")
    logger.info(f"Valid for {days_valid} days")

    return cert_path, key_path


def create_server_ssl_context(
    cert_path: Optional[Path] = None,
    key_path: Optional[Path] = None,
    auto_generate: bool = True,
) -> ssl.SSLContext:
    """Create SSL context for server

    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        auto_generate: If True, automatically generate certificate if not found

    Returns:
        SSLContext. Missing, incomplete or invalid identities raise an error.
    """
    # Use default paths if not provided
    if cert_path is None:
        cert_path = DEFAULT_CERT_FILE
    if key_path is None:
        key_path = DEFAULT_KEY_FILE

    # Check if certificate exists, generate if needed
    if not cert_path.exists() or not key_path.exists():
        if auto_generate and not cert_path.exists() and not key_path.exists():
            logger.info(
                "Certificate not found, generating new self-signed certificate..."
            )
            cert_path, key_path = generate_self_signed_cert(cert_path, key_path)
        else:
            raise FileNotFoundError(
                f"TLS requires both certificate {cert_path} and key {key_path}"
            )

    # Create SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(str(cert_path), str(key_path))

    # Configure SSL context for security
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.set_ciphers(
        "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
    )

    logger.info("TLS/SSL enabled for server")
    logger.debug("Server SSL context configuration:")
    logger.debug(f"  Certificate: {cert_path}")
    logger.debug(f"  Key: {key_path}")
    logger.debug("  Minimum TLS version: TLS 1.2")
    logger.debug("  Cipher suites: ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")
    return ssl_context


def create_client_ssl_context(
    verify_cert: bool = True, ca_path: Optional[Path] = None
) -> ssl.SSLContext:
    """Create SSL context for client

    Args:
        verify_cert: Verify server identity; False is an explicit insecure opt-out.
        ca_path: Trusted CA bundle or self-signed server certificate. If omitted,
            use the system trust store. An invalid path always raises an error.

    Returns:
        SSLContext configured for client
    """
    if verify_cert:
        ssl_context = ssl.create_default_context(
            cafile=str(ca_path) if ca_path is not None else None
        )
        logger.info("TLS/SSL enabled for client with certificate verification")
        logger.debug("Client SSL context configuration:")
        logger.debug("  Certificate verification: ENABLED")
        logger.debug(f"  CA certificate: {ca_path}")
        logger.debug("  Hostname verification: ENABLED")
    else:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        logger.warning(
            "TLS certificate verification explicitly disabled; server identity is not authenticated"
        )
        logger.debug("Client SSL context configuration:")
        logger.debug("  Certificate verification: DISABLED (accepting self-signed)")
        logger.debug("  Hostname verification: DISABLED")

    # Configure SSL context for security
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    logger.debug("  Minimum TLS version: TLS 1.2")

    return ssl_context


def check_cert_expiration(cert_path: Optional[Path] = None) -> Optional[datetime]:
    """Check certificate expiration date

    Args:
        cert_path: Path to certificate file

    Returns:
        Expiration datetime or None if cert doesn't exist or error
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        return None

    if cert_path is None:
        cert_path = DEFAULT_CERT_FILE

    if not cert_path.exists():
        return None

    try:
        with open(cert_path, "rb") as f:
            cert_data = f.read()

        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        return cert.not_valid_after
    except Exception as e:
        logger.error(f"Error checking certificate expiration: {e}")
        return None


def warn_if_cert_expiring_soon(
    cert_path: Optional[Path] = None, days_warning: int = 30
) -> bool:
    """Check if certificate is expiring soon and warn

    Args:
        cert_path: Path to certificate file
        days_warning: Warn if certificate expires within this many days

    Returns:
        True if certificate is expiring soon, False otherwise
    """
    expiration = check_cert_expiration(cert_path)
    if expiration is None:
        return False

    days_until_expiration = (expiration - datetime.utcnow()).days

    if days_until_expiration <= 0:
        logger.error(f"Certificate has expired! Expiration date: {expiration}")
        return True
    elif days_until_expiration <= days_warning:
        logger.warning(
            f"Certificate expires in {days_until_expiration} days! "
            f"Expiration date: {expiration}"
        )
        return True

    return False
