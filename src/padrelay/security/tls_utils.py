"""TLS/SSL utilities for secure communication"""
import ssl
import os
import ipaddress
from pathlib import Path
from datetime import datetime, timedelta
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
    common_name: str = "localhost"
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
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
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

    # Ensure directory exists
    ensure_cert_dir_exists()

    logger.info("Generating self-signed certificate...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create certificate subject and issuer (same for self-signed)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
        x509.NameAttribute(NameOID.LOCALITY_NAME, locality),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    # Build certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=days_valid)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Write private key to file
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Set key file permissions to owner-only (600)
    os.chmod(key_path, 0o600)

    # Write certificate to file
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Set cert file permissions to owner-only (600)
    os.chmod(cert_path, 0o600)

    logger.info(f"Certificate generated: {cert_path}")
    logger.info(f"Private key generated: {key_path}")
    logger.info(f"Valid for {days_valid} days")

    return cert_path, key_path


def create_server_ssl_context(
    cert_path: Optional[Path] = None,
    key_path: Optional[Path] = None,
    auto_generate: bool = True
) -> Optional[ssl.SSLContext]:
    """Create SSL context for server

    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        auto_generate: If True, automatically generate certificate if not found

    Returns:
        SSLContext or None if TLS is disabled
    """
    # Use default paths if not provided
    if cert_path is None:
        cert_path = DEFAULT_CERT_FILE
    if key_path is None:
        key_path = DEFAULT_KEY_FILE

    # Check if certificate exists, generate if needed
    if not cert_path.exists() or not key_path.exists():
        if auto_generate:
            logger.info("Certificate not found, generating new self-signed certificate...")
            cert_path, key_path = generate_self_signed_cert(cert_path, key_path)
        else:
            logger.error(f"Certificate not found: {cert_path}")
            logger.error(f"Key not found: {key_path}")
            return None

    # Create SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(str(cert_path), str(key_path))

    # Configure SSL context for security
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')

    logger.info("TLS/SSL enabled for server")
    logger.debug(f"Server SSL context configuration:")
    logger.debug(f"  Certificate: {cert_path}")
    logger.debug(f"  Key: {key_path}")
    logger.debug(f"  Minimum TLS version: TLS 1.2")
    logger.debug(f"  Cipher suites: ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")
    return ssl_context


def create_client_ssl_context(
    verify_cert: bool = False,
    ca_path: Optional[Path] = None
) -> ssl.SSLContext:
    """Create SSL context for client

    Args:
        verify_cert: If True, verify server certificate (requires CA certificate)
        ca_path: Path to CA certificate for verification (optional)

    Returns:
        SSLContext configured for client
    """
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    if verify_cert and ca_path and ca_path.exists():
        # Verify server certificate using CA
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.load_verify_locations(str(ca_path))
        logger.info("TLS/SSL enabled for client with certificate verification")
        logger.debug(f"Client SSL context configuration:")
        logger.debug(f"  Certificate verification: ENABLED")
        logger.debug(f"  CA certificate: {ca_path}")
        logger.debug(f"  Hostname verification: ENABLED")
    else:
        # Don't verify certificate (self-signed)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        if verify_cert:
            logger.warning(
                "Certificate verification requested but CA certificate not found. "
                "Proceeding without verification (insecure for production)."
            )
        logger.info("TLS/SSL enabled for client without certificate verification")
        logger.debug(f"Client SSL context configuration:")
        logger.debug(f"  Certificate verification: DISABLED (accepting self-signed)")
        logger.debug(f"  Hostname verification: DISABLED")

    # Configure SSL context for security
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    logger.debug(f"  Minimum TLS version: TLS 1.2")

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


def warn_if_cert_expiring_soon(cert_path: Optional[Path] = None, days_warning: int = 30) -> bool:
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
