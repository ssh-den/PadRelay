Changelog
=========

All notable changes to this project are documented here.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Version 1.1.0 (2025-11-06)
--------------------------

Added
~~~~~

**TLS/SSL Support:**

* Optional TLS/SSL encryption for TCP connections
* Automatic self-signed certificate generation
* Certificate expiration warnings
* TLS 1.2+ minimum version requirement
* Server ``--cert-path`` and ``--key-path`` options for custom certificates
* Client and server ``--enable-tls`` / ``--disable-tls`` flags
* Certificates stored in ``~/.padrelay/certs/`` directory

**Password Strength Warnings:**

* Non-enforcing password strength checking with recommendations
* Automatic password strength analysis on startup
* Detailed recommendations for improving weak passwords
* Warnings for very weak or commonly used passwords

**Security Enhancements:**

* Log sanitization to prevent log injection attacks
* Config file permission warnings for world-readable files
* 55 new security-focused tests

**Debug Logging:**

* Comprehensive debug mode via ``PADRELAY_DEBUG`` environment variable
* Detailed TLS connection logging
* Authentication flow logging
* See ``DEBUG_LOGGING.md`` for details

**Dependencies:**

* Added ``cryptography>=41.0.0`` for TLS support
* Added ``cffi>=1.15.0`` for cryptography backend

Changed
~~~~~~~

* TLS/SSL is now **enabled by default** for TCP connections (disable with ``--disable-tls``)
* Enhanced security warnings throughout the application
* Improved error messages for security-related issues
* Updated documentation with TLS setup guides

Fixed
~~~~~

* All 123 tests now pass (previously 10 async integration tests were failing)
* pytest-asyncio configuration issues resolved
* Various minor bug fixes

Security
~~~~~~~~

* Addresses **VULN-001** (No Network Encryption) - TLS/SSL now available
* Addresses **VULN-002** (Weak Password Enforcement) - password strength warnings implemented
* Addresses **VULN-003** (Passwords in Config Files) - file permission warnings added
* Addresses **VULN-004** (Log Injection Potential) - log sanitization implemented

Version 1.0.4 (2025-06-15)
--------------------------

Added
~~~~~

* ``padrelay-keymapper`` CLI tool for creating controller mapping files
* Interactive button and axis mapping
* Support for Xbox 360 and DualShock 4 virtual gamepad types
* Generated configuration files compatible with server and client

Version 1.0.3 (2025-06-14)
--------------------------

Fixed
~~~~~

* Synced GitHub release and PyPI version numbers to avoid mismatch
* Ensured correct artifacts attached to GitHub Releases

Version 1.0.2 (2025-06-14)
--------------------------

Fixed
~~~~~

* Corrected ``version`` field in ``pyproject.toml`` to match intended release

Version 1.0.1 (2025-06-14)
--------------------------

Added
~~~~~

**CI/CD:**

* GitHub Actions workflow for testing with pytest (``python-tests.yml``)
* GitHub Actions workflow for building and publishing releases on tag push (``release.yml``)
* Automated PyPI publishing on version tags

Version 1.0.0 (2025-06-14)
--------------------------

Initial release of PadRelay.

Features
~~~~~~~~

* **Client-server architecture** for transmitting gamepad input over network
* **Cross-platform client** supporting any OS with Python and pygame
* **Windows server** using vgamepad and ViGEmBus for virtual gamepads
* **TCP and UDP protocols** for different latency/reliability tradeoffs
* **Challenge-response authentication** for TCP connections
* **Token-based authentication** for UDP connections
* **PBKDF2 password hashing** for secure password storage
* **Rate limiting** to prevent denial-of-service attacks
* **Heartbeat mechanism** for connection keepalive (TCP)
* **Automatic reconnection** when connection drops
* **Configurable button and axis mappings**
* **Support for Xbox 360 and DualShock 4** virtual gamepads
* **Comprehensive logging** with automatic log rotation
* **Command-line tools:** ``padrelay-server``, ``padrelay-client``

Documentation
~~~~~~~~~~~~~

* README with installation and usage instructions
* Configuration reference (CONFIGURATION.md)
* Example configuration files
* MIT License

Links
-----

* `GitHub Repository <https://github.com/ssh-den/PadRelay>`_
* `PyPI Package <https://pypi.org/project/padrelay/>`_
* `Issue Tracker <https://github.com/ssh-den/PadRelay/issues>`_
* `Latest Release <https://github.com/ssh-den/PadRelay/releases/latest>`_
