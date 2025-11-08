TLS/SSL Setup Guide
===================

This guide covers setting up TLS/SSL encryption for secure PadRelay connections.

Overview
--------

PadRelay supports TLS/SSL encryption for TCP connections to protect against eavesdropping and man-in-the-middle attacks.

**Default Behavior:**

* TLS is **enabled by default** for TCP connections (version 1.1.0+)
* Self-signed certificates are automatically generated
* UDP does not support TLS (use VPN instead)

Quick Start
-----------

Using Auto-Generated Certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simplest way to use TLS is with auto-generated self-signed certificates:

**Server:**

.. code-block:: bash

   padrelay-server --config server_config.ini
   # TLS enabled by default, certificates auto-generated

**Client:**

.. code-block:: bash

   padrelay-client --config client_config.ini
   # TLS enabled by default

That's it! The server will create certificates on first run, and the client will connect securely.

Certificate Locations
---------------------

Auto-Generated Certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Certificates are stored in:

* **Linux/macOS:** ``~/.padrelay/certs/``
* **Windows:** ``%USERPROFILE%\.padrelay\certs\``

Files created:

* ``server.crt`` - Server certificate (public)
* ``server.key`` - Private key (keep secure!)

**Permissions:**

* Directory: ``700`` (owner only)
* Private key: ``600`` (owner read/write only)

Certificate Properties
~~~~~~~~~~~~~~~~~~~~~~

Auto-generated certificates have:

* **Algorithm:** RSA 2048-bit
* **Validity:** 365 days from creation
* **Subject:** CN=localhost
* **Self-signed:** Yes (not from trusted CA)

Viewing Certificate Details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To inspect a certificate:

.. code-block:: bash

   openssl x509 -in ~/.padrelay/certs/server.crt -text -noout

Using Custom Certificates
--------------------------

For production or better security, use certificates from a trusted Certificate Authority (CA).

Generating with OpenSSL
~~~~~~~~~~~~~~~~~~~~~~~~

1. **Generate private key:**

.. code-block:: bash

   openssl genrsa -out server.key 2048

2. **Create certificate signing request (CSR):**

.. code-block:: bash

   openssl req -new -key server.key -out server.csr

3. **Self-sign certificate (for testing):**

.. code-block:: bash

   openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

4. **Or submit CSR to CA for signing** (for production)

Using Let's Encrypt
~~~~~~~~~~~~~~~~~~~

For public-facing servers (not recommended for PadRelay), you can use Let's Encrypt:

.. code-block:: bash

   # Install certbot
   sudo apt-get install certbot  # Ubuntu/Debian

   # Generate certificate
   sudo certbot certonly --standalone -d your-domain.com

   # Use certificates
   padrelay-server \
     --cert-path /etc/letsencrypt/live/your-domain.com/fullchain.pem \
     --key-path /etc/letsencrypt/live/your-domain.com/privkey.pem

.. warning::
   Let's Encrypt requires public internet access and domain validation. Only use for public servers on your own domain.

Configuring Custom Certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Command-line:**

.. code-block:: bash

   padrelay-server \
     --cert-path /path/to/server.crt \
     --key-path /path/to/server.key

**Configuration file:**

.. code-block:: ini

   [server]
   cert_path = /path/to/server.crt
   key_path = /path/to/server.key

TLS Configuration
-----------------

TLS Version
~~~~~~~~~~~

PadRelay enforces minimum TLS version:

* **Minimum:** TLS 1.2
* **Recommended:** TLS 1.3 (if supported by Python/OpenSSL version)

Cipher Suites
~~~~~~~~~~~~~

PadRelay uses secure modern ciphers:

* ECDHE-ECDSA-AES256-GCM-SHA384
* ECDHE-RSA-AES256-GCM-SHA384
* ECDHE-ECDSA-CHACHA20-POLY1305
* ECDHE-RSA-CHACHA20-POLY1305
* DHE-RSA-AES256-GCM-SHA384

**Properties:**

* Perfect Forward Secrecy (PFS)
* Authenticated encryption (GCM, ChaCha20-Poly1305)
* No weak ciphers (RC4, DES, 3DES, MD5)

Disabling TLS
-------------

.. warning::
   Disabling TLS removes encryption. Only disable on trusted networks.

When to Disable
~~~~~~~~~~~~~~~

* Testing on localhost
* Already using VPN (WireGuard, OpenVPN)
* Using SSH tunnel for connection
* Incompatible network equipment

How to Disable
~~~~~~~~~~~~~~

**Server:**

.. code-block:: bash

   padrelay-server --disable-tls

**Client:**

.. code-block:: bash

   padrelay-client --disable-tls

**Configuration file:**

.. code-block:: ini

   [server]
   enable_tls = false

.. note::
   Both client and server must have the same TLS setting (both enabled or both disabled).

Certificate Management
----------------------

Certificate Expiration
~~~~~~~~~~~~~~~~~~~~~~~

PadRelay warns when certificates expire soon:

.. code-block:: text

   WARNING: TLS certificate expires in 15 days. Please renew certificate.

To check expiration:

.. code-block:: bash

   openssl x509 -in ~/.padrelay/certs/server.crt -noout -enddate

Renewing Certificates
~~~~~~~~~~~~~~~~~~~~~

**Auto-generated certificates:**

.. code-block:: bash

   # Delete old certificates
   rm ~/.padrelay/certs/server.*

   # Restart server to generate new ones
   padrelay-server --config server_config.ini

**Custom certificates:**

Follow your CA's renewal process, then replace the certificate files and restart the server.

Certificate Rotation
~~~~~~~~~~~~~~~~~~~~

For security best practices:

1. Rotate certificates every 90-365 days
2. Use strong key lengths (minimum 2048-bit RSA)
3. Keep private keys secure (permissions 600)
4. Don't reuse certificates across services

Troubleshooting TLS
-------------------

TLS Handshake Failed
~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: TLS handshake failed
   ERROR: SSL: WRONG_VERSION_NUMBER

**Causes and Solutions:**

1. **Client/server TLS mismatch:**

   Ensure both have TLS enabled or both have it disabled.

2. **Certificate issues:**

   Check certificate is valid and not expired.

3. **System time mismatch:**

   Synchronize system clocks on both machines.

4. **Incompatible TLS versions:**

   Update Python and OpenSSL to support TLS 1.2+.

Certificate Validation Failed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Certificate verification failed

**Solutions:**

1. Using self-signed certificates is expected (client ignores validation)
2. For custom CA certificates, ensure CA cert is in system trust store
3. Check certificate hostname matches server address

Permission Denied
~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Permission denied: ~/.padrelay/certs/server.key

**Solutions:**

.. code-block:: bash

   # Fix permissions
   chmod 600 ~/.padrelay/certs/server.key
   chmod 700 ~/.padrelay/certs/

Certificate Not Found
~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Certificate file not found

**Solutions:**

1. Let PadRelay auto-generate certificates (remove ``cert_path`` config)
2. Verify certificate path is correct
3. Check file permissions allow reading

Debug TLS Issues
~~~~~~~~~~~~~~~~

Enable debug logging to see detailed TLS information:

.. code-block:: bash

   export PADRELAY_DEBUG=1
   padrelay-server --config server_config.ini

Debug logs show:

* SSL context configuration
* Certificate paths
* TLS version negotiated
* Cipher suite used
* Handshake details

Security Considerations
-----------------------

Self-Signed Certificates
~~~~~~~~~~~~~~~~~~~~~~~~

**Advantages:**

* Free and easy to generate  
* Provides encryption  
* No certificate authority required  

**Limitations:**

* No identity verification  
* Can be vulnerable to man-in-the-middle attacks if the first connection is intercepted  
* May trigger certificate warnings in some tools  

**Recommendation:**  
Suitable for private or controlled networks where the connection path is trusted.

CA-Signed Certificates
~~~~~~~~~~~~~~~~~~~~~~

**Advantages:**

* Verifies server identity  
* Protects against man-in-the-middle attacks  
* Trusted by most clients by default  

**Limitations:**

* May involve cost (unless using Let's Encrypt)  
* More complex setup  
* Typically requires a registered domain name  

**Recommendation:**  
Use for production environments or when strong identity verification is required.

Network Security
~~~~~~~~~~~~~~~~

TLS protects data in transit, but:

* Still use strong passwords
* Still use VPN for untrusted networks
* Still avoid public internet exposure
* Still keep software updated

VPN vs TLS
~~~~~~~~~~

**Use both for maximum security:**

* VPN provides network-level encryption and access control
* TLS provides application-level encryption
* Defense in depth approach

**Or choose based on needs:**

* **VPN only:** Simpler, protects all traffic, use UDP for lower latency
* **TLS only:** No VPN required, per-application security, TCP only

Testing TLS Connection
----------------------

Verify TLS is Working
~~~~~~~~~~~~~~~~~~~~~

Check server logs for:

.. code-block:: text

   INFO: TLS/SSL enabled
   INFO: TLS version: TLSv1.3
   INFO: Cipher: TLS_AES_256_GCM_SHA384

Using OpenSSL Client
~~~~~~~~~~~~~~~~~~~~

Test TLS connection:

.. code-block:: bash

   openssl s_client -connect SERVER_IP:9999 -tls1_2

Should show certificate details and "Verify return code: 18 (self signed certificate)" for auto-generated certs.

Best Practices
--------------

1. **Keep TLS enabled** for all production deployments
2. **Use strong passwords** even with TLS
3. **Rotate certificates** regularly
4. **Secure private keys** with proper permissions
5. **Monitor expiration** dates
6. **Use VPN** for additional security
7. **Update software** to get latest TLS fixes

See Also
--------

* :doc:`../security` - Security overview
* :doc:`server` - Server configuration
* :doc:`client` - Client configuration
* :doc:`troubleshooting` - Troubleshooting guide
