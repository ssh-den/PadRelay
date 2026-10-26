"""Tests for TLS utilities"""
import pytest
import ssl
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from padrelay.security.tls_utils import (
    generate_self_signed_cert,
    create_server_ssl_context,
    create_client_ssl_context,
    check_cert_expiration,
    warn_if_cert_expiring_soon,
    get_default_cert_paths,
    ensure_cert_dir_exists,
)


class TestCertificateGeneration:
    """Test certificate generation"""

    def test_generate_self_signed_cert(self, tmp_path):
        """Test self-signed certificate generation"""
        cert_path = tmp_path / "test.crt"
        key_path = tmp_path / "test.key"

        result_cert, result_key = generate_self_signed_cert(
            cert_path=cert_path,
            key_path=key_path,
            days_valid=365
        )

        # Check that files were created
        assert cert_path.exists()
        assert key_path.exists()

        # Check that returned paths match
        assert result_cert == cert_path
        assert result_key == key_path

        # Check file permissions (600 = owner read/write only)
        import stat
        cert_stat = cert_path.stat()
        key_stat = key_path.stat()

        # Key should be readable and writable by owner only
        assert key_stat.st_mode & 0o777 == 0o600

    def test_generate_cert_with_custom_params(self, tmp_path):
        """Test certificate generation with custom parameters"""
        cert_path = tmp_path / "custom.crt"
        key_path = tmp_path / "custom.key"

        generate_self_signed_cert(
            cert_path=cert_path,
            key_path=key_path,
            days_valid=30,
            country="GB",
            organization="TestOrg",
            common_name="test.local"
        )

        assert cert_path.exists()
        assert key_path.exists()

    def test_default_cert_paths(self):
        """Test getting default certificate paths"""
        cert_path, key_path = get_default_cert_paths()

        assert isinstance(cert_path, Path)
        assert isinstance(key_path, Path)
        assert str(cert_path).endswith("server.crt")
        assert str(key_path).endswith("server.key")

    def test_ensure_cert_dir_exists(self, tmp_path):
        """Test certificate directory creation"""
        # Temporarily override the default cert dir
        import padrelay.security.tls_utils as tls_module
        original_cert_dir = tls_module.DEFAULT_CERT_DIR
        tls_module.DEFAULT_CERT_DIR = tmp_path / "certs"

        try:
            cert_dir = ensure_cert_dir_exists()
            assert cert_dir.exists()
            assert cert_dir.is_dir()

            # Check permissions (700 = owner only)
            import stat
            dir_stat = cert_dir.stat()
            assert dir_stat.st_mode & 0o777 == 0o700
        finally:
            tls_module.DEFAULT_CERT_DIR = original_cert_dir


class TestSSLContextCreation:
    """Test SSL context creation"""

    def test_create_server_ssl_context_auto_generate(self, tmp_path):
        """Test server SSL context creation with auto-generation"""
        cert_path = tmp_path / "server.crt"
        key_path = tmp_path / "server.key"

        ssl_context = create_server_ssl_context(
            cert_path=cert_path,
            key_path=key_path,
            auto_generate=True
        )

        assert ssl_context is not None
        assert isinstance(ssl_context, ssl.SSLContext)
        # Verify files were created
        assert cert_path.exists()
        assert key_path.exists()

    def test_create_server_ssl_context_existing_cert(self, tmp_path):
        """Test server SSL context with existing certificate"""
        cert_path = tmp_path / "existing.crt"
        key_path = tmp_path / "existing.key"

        # Generate certificate first
        generate_self_signed_cert(cert_path=cert_path, key_path=key_path)

        # Create SSL context with existing cert
        ssl_context = create_server_ssl_context(
            cert_path=cert_path,
            key_path=key_path,
            auto_generate=False
        )

        assert ssl_context is not None
        assert isinstance(ssl_context, ssl.SSLContext)

    def test_create_server_ssl_context_missing_cert_no_auto(self, tmp_path):
        """Test server SSL context without cert and auto_generate=False"""
        cert_path = tmp_path / "missing.crt"
        key_path = tmp_path / "missing.key"

        ssl_context = create_server_ssl_context(
            cert_path=cert_path,
            key_path=key_path,
            auto_generate=False
        )

        # Should return None when cert doesn't exist and auto_generate=False
        assert ssl_context is None

    def test_create_client_ssl_context_no_verify(self):
        """Test client SSL context without verification"""
        ssl_context = create_client_ssl_context(verify_cert=False)

        assert ssl_context is not None
        assert isinstance(ssl_context, ssl.SSLContext)
        assert ssl_context.verify_mode == ssl.CERT_NONE
        assert ssl_context.check_hostname is False

    def test_create_client_ssl_context_with_verify_no_ca(self):
        """Test client SSL context with verification but no CA"""
        ssl_context = create_client_ssl_context(verify_cert=True, ca_path=None)

        assert ssl_context is not None
        # Should fall back to no verification
        assert ssl_context.verify_mode == ssl.CERT_NONE

    def test_create_client_ssl_context_with_ca(self, tmp_path):
        """Test client SSL context with CA certificate"""
        # Generate a certificate to use as CA
        ca_path = tmp_path / "ca.crt"
        key_path = tmp_path / "ca.key"
        generate_self_signed_cert(cert_path=ca_path, key_path=key_path)

        ssl_context = create_client_ssl_context(verify_cert=True, ca_path=ca_path)

        assert ssl_context is not None
        assert isinstance(ssl_context, ssl.SSLContext)
        assert ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert ssl_context.check_hostname is True

    def test_ssl_context_minimum_tls_version(self, tmp_path):
        """Test that SSL contexts use minimum TLS 1.2"""
        cert_path = tmp_path / "test.crt"
        key_path = tmp_path / "test.key"

        server_context = create_server_ssl_context(
            cert_path=cert_path,
            key_path=key_path,
            auto_generate=True
        )

        client_context = create_client_ssl_context(verify_cert=False)

        # Both contexts should require at least TLS 1.2
        assert server_context.minimum_version == ssl.TLSVersion.TLSv1_2
        assert client_context.minimum_version == ssl.TLSVersion.TLSv1_2


class TestCertificateExpiration:
    """Test certificate expiration checking"""

    def test_check_cert_expiration(self, tmp_path):
        """Test certificate expiration date checking"""
        cert_path = tmp_path / "test.crt"
        key_path = tmp_path / "test.key"

        generate_self_signed_cert(
            cert_path=cert_path,
            key_path=key_path,
            days_valid=365
        )

        expiration = check_cert_expiration(cert_path)

        assert expiration is not None
        assert isinstance(expiration, datetime)
        # Should expire approximately 365 days from now
        days_until_expiration = (expiration - datetime.utcnow()).days
        assert 360 <= days_until_expiration <= 366

    def test_check_cert_expiration_missing_file(self, tmp_path):
        """Test certificate expiration check with missing file"""
        cert_path = tmp_path / "missing.crt"
        expiration = check_cert_expiration(cert_path)

        assert expiration is None

    def test_warn_if_cert_expiring_soon(self, tmp_path):
        """Test warning for soon-to-expire certificate"""
        cert_path = tmp_path / "test.crt"
        key_path = tmp_path / "test.key"

        # Generate cert valid for only 10 days
        generate_self_signed_cert(
            cert_path=cert_path,
            key_path=key_path,
            days_valid=10
        )

        # Should warn if expiring within 30 days
        result = warn_if_cert_expiring_soon(cert_path, days_warning=30)
        assert result is True

    def test_warn_if_cert_not_expiring_soon(self, tmp_path):
        """Test no warning for certificate not expiring soon"""
        cert_path = tmp_path / "test.crt"
        key_path = tmp_path / "test.key"

        # Generate cert valid for 365 days
        generate_self_signed_cert(
            cert_path=cert_path,
            key_path=key_path,
            days_valid=365
        )

        # Should not warn if expiring in more than 30 days
        result = warn_if_cert_expiring_soon(cert_path, days_warning=30)
        assert result is False


class TestIntegration:
    """Integration tests for TLS utilities"""

    def test_full_tls_setup(self, tmp_path):
        """Test complete TLS setup flow"""
        cert_path = tmp_path / "server.crt"
        key_path = tmp_path / "server.key"

        # 1. Generate certificate
        generate_self_signed_cert(cert_path=cert_path, key_path=key_path)

        # 2. Create server SSL context
        server_context = create_server_ssl_context(
            cert_path=cert_path,
            key_path=key_path,
            auto_generate=False
        )

        # 3. Create client SSL context
        client_context = create_client_ssl_context(verify_cert=False)

        # 4. Check expiration
        expiration = check_cert_expiration(cert_path)

        assert server_context is not None
        assert client_context is not None
        assert expiration is not None

    @pytest.mark.asyncio
    async def test_tls_connection_handshake(self, tmp_path):
        """Test TLS connection establishment between client and server"""
        import asyncio

        cert_path = tmp_path / "server.crt"
        key_path = tmp_path / "server.key"

        # Generate certificate
        generate_self_signed_cert(cert_path=cert_path, key_path=key_path)

        # Create SSL contexts
        server_context = create_server_ssl_context(
            cert_path=cert_path,
            key_path=key_path,
            auto_generate=False
        )
        client_context = create_client_ssl_context(verify_cert=False)

        assert server_context is not None
        assert client_context is not None

        # Test data to exchange
        test_message = b"Hello TLS"
        received_message = None

        async def handle_client(reader, writer):
            """Server handler to receive and echo data"""
            nonlocal received_message
            data = await reader.read(100)
            received_message = data
            writer.write(data)  # Echo back
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        # Start server
        server = await asyncio.start_server(
            handle_client,
            '127.0.0.1',
            0,  # Use any available port
            ssl=server_context
        )

        addr = server.sockets[0].getsockname()
        port = addr[1]

        async with server:
            # Start server task
            server_task = asyncio.create_task(server.serve_forever())

            try:
                # Connect client
                reader, writer = await asyncio.open_connection(
                    '127.0.0.1',
                    port,
                    ssl=client_context,
                    server_hostname='localhost'
                )

                # Verify TLS connection
                ssl_object = writer.get_extra_info('ssl_object')
                assert ssl_object is not None, "SSL object should exist"

                # Verify TLS version
                tls_version = ssl_object.version()
                assert tls_version is not None, "TLS version should be available"
                assert 'TLSv1' in tls_version, f"Expected TLS version, got {tls_version}"

                # Verify cipher
                cipher = ssl_object.cipher()
                assert cipher is not None, "Cipher should be available"
                assert len(cipher) == 3, "Cipher tuple should have 3 elements"

                # Send test message
                writer.write(test_message)
                await writer.drain()

                # Receive echo
                echo = await reader.read(100)
                assert echo == test_message, "Echo should match sent message"

                # Close connection
                writer.close()
                await writer.wait_closed()

                # Verify server received the message
                assert received_message == test_message

            finally:
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
