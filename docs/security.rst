Security
========

This document covers security features, best practices, and considerations when using PadRelay.

Security Model
--------------

PadRelay implements multiple security layers:

1. **Authentication:** Verify client identity before accepting input
2. **Encryption:** Optional TLS/SSL for TCP connections
3. **Rate Limiting:** Prevent denial-of-service attacks
4. **Input Validation:** Sanitize all incoming data
5. **Secure Storage:** Hash passwords, sanitize logs

Threat Model
------------

Assumptions
~~~~~~~~~~~

* **Trusted Network:** PadRelay is designed for use on private networks (home LAN, VPN)
* **Physical Security:** Attacker does not have physical access to client or server
* **Software Integrity:** PadRelay code has not been modified by attacker

Threats Addressed
~~~~~~~~~~~~~~~~~

1. **Unauthorized Access:** Attackers cannot control virtual gamepad without password
2. **Man-in-the-Middle (TCP/TLS):** Encrypted connections prevent eavesdropping
3. **Replay Attacks:** Challenges and timestamps prevent message replay
4. **Denial of Service:** Rate limiting mitigates simple DoS attacks
5. **Password Disclosure:** Passwords are hashed before storage
6. **Log Injection:** Log sanitization prevents malicious log entries

Threats Not Addressed
~~~~~~~~~~~~~~~~~~~~~

.. warning::
   PadRelay is **not designed** to protect against:

   * **Network Attackers (UDP):** UDP mode has no encryption
   * **Advanced DoS:** Sophisticated distributed attacks may bypass rate limits
   * **Malware:** If client or server is compromised, attacker has full control
   * **Traffic Analysis:** Even with TLS, traffic patterns may reveal information
   * **Public Internet:** Never expose PadRelay directly to the internet

Authentication
--------------

Password-Based Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PadRelay uses password-based authentication with different mechanisms for TCP and UDP.

Password Hashing
^^^^^^^^^^^^^^^^

Passwords are hashed using **PBKDF2-HMAC-SHA256**:

* **Algorithm:** PBKDF2 (Password-Based Key Derivation Function 2)
* **Hash Function:** HMAC-SHA256
* **Iterations:** 100,000 (configurable, default)
* **Salt:** 16 bytes (128 bits) of random data
* **Output:** 32 bytes (256 bits)

**Storage Format:**

.. code-block:: text

   pbkdf2_sha256$iterations$salt_hex$hash_hex

**Example:**

.. code-block:: text

   pbkdf2_sha256$100000$abc123def456...$deadbeef1234...

TCP Challenge-Response
~~~~~~~~~~~~~~~~~~~~~~

TCP connections use a challenge-response protocol:

1. **Challenge Generation:** Server generates 32 bytes of random data
2. **Parameter Exchange:** Server sends challenge, salt, and iteration count
3. **Key Derivation:** Client derives key using PBKDF2 with server parameters
4. **Response Computation:** Client computes HMAC-SHA256(key, challenge)
5. **Verification:** Server compares response with expected value
6. **Access Decision:** Match grants access, mismatch denies access

**Security Properties:**

* **No Password Transmission:** Password never sent over network
* **Single-Use Challenge:** Each challenge used only once
* **Brute-Force Resistance:** PBKDF2 iterations slow down attacks
* **No Replay:** Challenge-response cannot be replayed

UDP Token Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~

UDP messages include time-based authentication tokens:

1. **Key Derivation:** Client derives key using PBKDF2 (once)
2. **Token Computation:** For each message:

   .. code-block:: python

      token = HMAC-SHA256(key, message_json + timestamp)

3. **Token Validation:** Server recomputes token and compares
4. **Timestamp Check:** Server verifies timestamp is recent (≤60 seconds old)

**Security Properties:**

* **Per-Message Authentication:** Each message independently verified
* **Replay Protection:** Timestamps prevent replay after 60-second window
* **No Password Transmission:** Password never sent over network

**Limitations:**

* **Clock Synchronization:** Client and server clocks must be within 60 seconds
* **No Encryption:** UDP does not support TLS

Encryption
----------

TLS/SSL Support
~~~~~~~~~~~~~~~

PadRelay supports TLS/SSL encryption for TCP connections:

* **Enabled by Default:** TCP connections use TLS by default (v1.1.0+)
* **Minimum Version:** TLS 1.2
* **Recommended Version:** TLS 1.3
* **Cipher Suites:** Modern, secure ciphers (ECDHE, AES-GCM, ChaCha20)

Certificate Management
~~~~~~~~~~~~~~~~~~~~~~

Self-Signed Certificates
^^^^^^^^^^^^^^^^^^^^^^^^

PadRelay automatically generates self-signed certificates:

* **Location:** ``~/.padrelay/certs/`` (Linux/Mac) or ``%USERPROFILE%\.padrelay\certs\`` (Windows)
* **Files:** ``server.crt`` (certificate) and ``server.key`` (private key)
* **Algorithm:** RSA 2048-bit
* **Validity:** 365 days
* **Subject:** CN=localhost

**Security Note:** Self-signed certificates provide encryption but not identity verification. They protect against passive eavesdropping but not active man-in-the-middle attacks.

Custom Certificates
^^^^^^^^^^^^^^^^^^^

For better security, use certificates from a trusted CA:

.. code-block:: bash

   padrelay-server --cert-path /path/to/cert.pem --key-path /path/to/key.pem

Or configure in INI file:

.. code-block:: ini

   [server]
   cert_path = /path/to/cert.pem
   key_path = /path/to/key.pem

Certificate Expiration
^^^^^^^^^^^^^^^^^^^^^^^

PadRelay warns when certificates will expire within 30 days:

.. code-block:: text

   WARNING: TLS certificate expires in 15 days. Please renew certificate.

To renew, delete old certificates and restart server to generate new ones:

.. code-block:: bash

   rm ~/.padrelay/certs/server.*
   padrelay-server --config server_config.ini

Disabling TLS
~~~~~~~~~~~~~

.. warning::
   Disabling TLS is **not recommended**. Only disable on trusted networks.

To disable TLS:

.. code-block:: bash

   padrelay-server --disable-tls
   padrelay-client --disable-tls

When to disable TLS:

* Testing on localhost
* Already using VPN or SSH tunnel
* Network device doesn't support TLS

Rate Limiting
-------------

Purpose
~~~~~~~

Rate limiting prevents clients from overwhelming the server with requests:

* **Denial of Service:** Limits impact of malicious clients
* **Resource Protection:** Prevents server resource exhaustion
* **Fair Usage:** Ensures all clients get fair access

Configuration
~~~~~~~~~~~~~

.. code-block:: ini

   [server]
   rate_limit_window = 60        # Time window in seconds
   max_requests = 100            # Max requests per window (TCP)
   max_requests = 6000           # Max requests per window (UDP)
   block_duration = 2            # Block duration in seconds

Algorithm
~~~~~~~~~

PadRelay uses a sliding window rate limiter:

1. **Track Requests:** Count requests per client IP in time window
2. **Check Limit:** If count > ``max_requests``, block client
3. **Block Client:** Reject requests for ``block_duration`` seconds
4. **Reset:** After block expires, client can try again

**Example:**

* Window: 60 seconds
* Max requests: 100
* Client sends 150 requests in 60 seconds
* Server blocks client for 2 seconds
* Client must wait before reconnecting

Bypass
~~~~~~

To disable rate limiting (not recommended):

.. code-block:: ini

   [server]
   max_requests = 999999

Input Validation
----------------

All input is validated before processing:

Button Validation
~~~~~~~~~~~~~~~~~

* Button indices must be non-negative integers
* Out-of-range buttons are logged and ignored

Axis Validation
~~~~~~~~~~~~~~~

* Axis values must be floats between -1.0 and 1.0
* Out-of-range values are clamped to valid range
* Dead zones applied to prevent drift

Message Validation
~~~~~~~~~~~~~~~~~~

* Messages must be valid JSON
* Required fields must be present
* Protocol version must match
* Unknown fields are ignored (forward compatibility)

Secure Coding Practices
-----------------------

Log Sanitization
~~~~~~~~~~~~~~~~

Logs are sanitized to prevent log injection attacks:

* Newlines replaced with spaces
* Control characters removed
* Passwords and tokens never logged
* Sensitive data redacted

Example sanitization:

.. code-block:: python

   # Input: "User\nINFO: Admin logged in"
   # Output: "User INFO: Admin logged in"

File Permissions
~~~~~~~~~~~~~~~~

PadRelay checks configuration file permissions:

.. code-block:: text

   WARNING: Configuration file is world-readable!
   Consider setting permissions to 600: chmod 600 config.ini

Recommended permissions:

* Configuration files: ``600`` (owner read/write only)
* Log directory: ``700`` (owner read/write/execute only)
* Certificate files: ``600`` (owner read/write only)

Secrets Management
~~~~~~~~~~~~~~~~~~

Best practices for managing secrets:

1. **Environment Variables:** Use ``PASSWORD`` or ``PASSWORD_HASH`` env vars
2. **Pre-Hashed Passwords:** Hash passwords before storing in config
3. **Secure Storage:** Store config files with restricted permissions
4. **No Version Control:** Never commit passwords to git

.. code-block:: bash

   # Good: Environment variable
   export PASSWORD="my_secure_password"
   padrelay-server --config server_config.ini

   # Better: Pre-hashed password
   export PASSWORD_HASH="pbkdf2_sha256$100000$abc...$def..."
   padrelay-server --config server_config.ini

Best Practices
--------------

Network Security
~~~~~~~~~~~~~~~~

1. **Use VPN:** Run PadRelay over VPN (WireGuard, OpenVPN)
2. **Private Networks:** Use only on trusted private networks
3. **Firewall:** Configure firewall to allow only necessary connections
4. **No Public Internet:** Never expose server directly to internet

.. code-block:: bash

   # Good: Bind to private IP
   host = 192.168.1.100

   # Bad: Bind to all interfaces on public internet
   host = 0.0.0.0  # Only safe on private network or with firewall

Password Security
~~~~~~~~~~~~~~~~~

1. **Strong Passwords:** Use 12+ character passwords with mixed case, numbers, symbols
2. **Unique Passwords:** Don't reuse passwords from other services
3. **Password Managers:** Use a password manager to generate and store passwords
4. **Regular Rotation:** Change passwords periodically

PadRelay warns about weak passwords:

.. code-block:: text

   WARNING: Password is weak!
   Recommendations:
   - Use at least 12 characters
   - Include uppercase and lowercase letters
   - Include numbers and symbols
   - Avoid common passwords

Certificate Security
~~~~~~~~~~~~~~~~~~~~

1. **Use TLS:** Enable TLS for all TCP connections
2. **Custom Certificates:** Use CA-signed certificates for production
3. **Certificate Rotation:** Renew certificates before expiration
4. **Protect Private Keys:** Secure private keys with ``600`` permissions

Operational Security
~~~~~~~~~~~~~~~~~~~~

1. **Keep Updated:** Update PadRelay to latest version for security patches
2. **Monitor Logs:** Review logs for suspicious activity
3. **Debug Mode:** Disable debug mode in production (``PADRELAY_DEBUG=0``)
4. **Least Privilege:** Run server with minimal necessary permissions

Debug Logging
~~~~~~~~~~~~~

Debug mode logs detailed information but should be disabled in production:

.. code-block:: bash

   # Development: Enable debug logging
   export PADRELAY_DEBUG=1
   padrelay-server --config server_config.ini

   # Production: Disable debug logging
   unset PADRELAY_DEBUG
   padrelay-server --config server_config.ini

Security Audit Report
---------------------

PadRelay has undergone security review. See ``SECURITY_AUDIT_REPORT.md`` in the repository for details.

**Version 1.1.0 Improvements:**

* ✅ TLS/SSL encryption for TCP connections
* ✅ Password strength validation and warnings
* ✅ Log sanitization to prevent injection attacks
* ✅ Configuration file permission warnings
* ✅ 55 new security-focused tests

Reporting Security Issues
-------------------------

If you discover a security vulnerability in PadRelay:

1. **Do not** open a public GitHub issue
2. Email the maintainer at: sshden@duck.com
3. Include:

   * Description of vulnerability
   * Steps to reproduce
   * Potential impact
   * Suggested fix (if available)

You will receive a response within 48 hours. Security issues are handled with priority.

See Also
--------

* :doc:`user_guide/tls_setup` - TLS setup guide
* :doc:`configuration` - Configuration reference
* :doc:`protocol` - Protocol specification
* `SECURITY_AUDIT_REPORT.md <https://github.com/ssh-den/PadRelay/blob/main/SECURITY_AUDIT_REPORT.md>`_ - Full security audit
