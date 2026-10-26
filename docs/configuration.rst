Configuration Reference
=======================

This document describes every configuration option and command-line flag available in PadRelay.

Configuration Files
-------------------

PadRelay uses INI-format configuration files with multiple sections. Example files are provided in the ``config/`` directory of the repository.

Configuration Priority
~~~~~~~~~~~~~~~~~~~~~~

Settings are applied in the following order (highest priority first):

1. Environment variables (``PASSWORD``, ``PASSWORD_HASH``, ``PADRELAY_LOG_DIR``, ``PADRELAY_DEBUG``)
2. Command-line arguments
3. Configuration file values
4. Default values

Client Configuration
--------------------

Network Settings
~~~~~~~~~~~~~~~~

**Section:** ``[network]``

.. list-table::
   :header-rows: 1
   :widths: 20 15 50 15

   * - Option
     - Type
     - Description
     - Default
   * - ``server_ip``
     - string
     - IP address of the gamepad server
     - ``127.0.0.1``
   * - ``server_port``
     - integer
     - Port number the server listens on
     - ``9999``
   * - ``protocol``
     - string
     - Transport protocol: ``tcp`` or ``udp``
     - ``tcp``
   * - ``password``
     - string
     - Authentication password (plaintext or hashed)
     - *(required)*
   * - ``password_hash``
     - string
     - Pre-hashed password (overrides ``password``)
     - ``None``

Joystick Settings
~~~~~~~~~~~~~~~~~

**Section:** ``[joystick]``

.. list-table::
   :header-rows: 1
   :widths: 20 15 50 15

   * - Option
     - Type
     - Description
     - Default
   * - ``index``
     - integer
     - Index of the physical gamepad (0 for first, 1 for second, etc.)
     - ``0``

Client Settings
~~~~~~~~~~~~~~~

**Section:** ``[client]``

.. list-table::
   :header-rows: 1
   :widths: 20 15 50 15

   * - Option
     - Type
     - Description
     - Default
   * - ``update_rate``
     - integer
     - Frequency of input updates sent to server (Hz)
     - ``60``

Client Command-Line Flags
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   padrelay-client [OPTIONS]

   Options:
     --server-ip TEXT              IP address of the server
     --server-port INTEGER         Server port number
     --protocol [tcp|udp]          Transport protocol
     --joystick-index INTEGER      Index of joystick to use
     --update-rate INTEGER         Update rate in Hz
     --password TEXT               Authentication password
     --password-hash TEXT          Pre-hashed password (overrides --password)
     --enable-tls                  Enable TLS/SSL encryption (default for TCP)
     --disable-tls                 Disable TLS/SSL encryption
     --config PATH                 Path to configuration file
     --help                        Show help message and exit

Server Configuration
--------------------

Server Settings
~~~~~~~~~~~~~~~

**Section:** ``[server]``

.. list-table::
   :header-rows: 1
   :widths: 20 15 50 15

   * - Option
     - Type
     - Description
     - Default
   * - ``host``
     - string
     - Interface to bind to (``0.0.0.0`` for all, ``127.0.0.1`` for localhost)
     - ``127.0.0.1``
   * - ``port``
     - integer
     - Port to listen on
     - ``9999``
   * - ``protocol``
     - string
     - Transport protocol: ``tcp`` or ``udp``
     - ``tcp``
   * - ``password``
     - string
     - Authentication password (auto-hashed on first run)
     - *(required)*
   * - ``rate_limit_window``
     - integer
     - Time window for rate limiting (seconds)
     - ``60``
   * - ``max_requests``
     - integer
     - Maximum requests per window (100 for TCP, 6000 for UDP)
     - ``100`` / ``6000``
   * - ``block_duration``
     - integer
     - Duration to block clients exceeding rate limit (seconds)
     - ``2``

Virtual Gamepad Settings
~~~~~~~~~~~~~~~~~~~~~~~~

**Section:** ``[vgamepad]``

.. list-table::
   :header-rows: 1
   :widths: 20 15 50 15

   * - Option
     - Type
     - Description
     - Default
   * - ``type``
     - string
     - Virtual controller type: ``xbox360`` or ``ds4``
     - ``xbox360``

Button Mapping
~~~~~~~~~~~~~~

**Sections:** ``[button_mapping_xbox360]`` and ``[button_mapping_ds4]``

Maps physical button numbers to virtual gamepad button constants. Example:

.. code-block:: ini

   [button_mapping_xbox360]
   0 = XUSB_GAMEPAD_A
   1 = XUSB_GAMEPAD_B
   2 = XUSB_GAMEPAD_X
   3 = XUSB_GAMEPAD_Y
   4 = XUSB_GAMEPAD_LEFT_SHOULDER
   5 = XUSB_GAMEPAD_RIGHT_SHOULDER
   6 = XUSB_GAMEPAD_BACK
   7 = XUSB_GAMEPAD_START
   8 = XUSB_GAMEPAD_LEFT_THUMB
   9 = XUSB_GAMEPAD_RIGHT_THUMB

Available Xbox 360 buttons:

* ``XUSB_GAMEPAD_A``, ``XUSB_GAMEPAD_B``, ``XUSB_GAMEPAD_X``, ``XUSB_GAMEPAD_Y``
* ``XUSB_GAMEPAD_LEFT_SHOULDER``, ``XUSB_GAMEPAD_RIGHT_SHOULDER``
* ``XUSB_GAMEPAD_BACK``, ``XUSB_GAMEPAD_START``
* ``XUSB_GAMEPAD_LEFT_THUMB``, ``XUSB_GAMEPAD_RIGHT_THUMB``
* ``XUSB_GAMEPAD_DPAD_UP``, ``XUSB_GAMEPAD_DPAD_DOWN``
* ``XUSB_GAMEPAD_DPAD_LEFT``, ``XUSB_GAMEPAD_DPAD_RIGHT``

Available DualShock 4 buttons:

* ``DS4_BUTTON_CROSS``, ``DS4_BUTTON_CIRCLE``, ``DS4_BUTTON_SQUARE``, ``DS4_BUTTON_TRIANGLE``
* ``DS4_BUTTON_SHOULDER_LEFT``, ``DS4_BUTTON_SHOULDER_RIGHT``
* ``DS4_BUTTON_TRIGGER_LEFT``, ``DS4_BUTTON_TRIGGER_RIGHT``
* ``DS4_BUTTON_SHARE``, ``DS4_BUTTON_OPTIONS``
* ``DS4_BUTTON_THUMB_LEFT``, ``DS4_BUTTON_THUMB_RIGHT``
* ``DS4_DPAD_*`` (directions)

Axis Mapping
~~~~~~~~~~~~

**Section:** ``[axis_mapping]``

Maps axis names to physical axis indices:

.. code-block:: ini

   [axis_mapping]
   left_stick_x = 0
   left_stick_y = 1
   right_stick_x = 2
   right_stick_y = 3
   trigger_left = 4
   trigger_right = 5

Axis Options
~~~~~~~~~~~~

**Section:** ``[axis_options]``

.. list-table::
   :header-rows: 1
   :widths: 25 15 45 15

   * - Option
     - Type
     - Description
     - Default
   * - ``dead_zone``
     - float
     - Minimum absolute value to register stick movement (0.0 - 1.0)
     - ``0.1``
   * - ``trigger_threshold``
     - float
     - Minimum trigger value to register as pressed (0.0 - 1.0)
     - ``0.1``
   * - ``invert_left_y``
     - boolean
     - Invert Y-axis for left stick
     - ``false``
   * - ``invert_right_y``
     - boolean
     - Invert Y-axis for right stick
     - ``false``

Server Command-Line Flags
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   padrelay-server [OPTIONS]

   Options:
     --host TEXT                   Interface to bind to
     --port INTEGER                Port to listen on
     --protocol [tcp|udp]          Transport protocol
     --password TEXT               Authentication password
     --gamepad-type [xbox360|ds4]  Virtual gamepad type
     --rate-limit-window INTEGER   Rate limit time window (seconds)
     --max-requests INTEGER        Maximum requests per window
     --block-duration INTEGER      Block duration for rate-limited clients
     --enable-tls                  Enable TLS/SSL encryption (default for TCP)
     --disable-tls                 Disable TLS/SSL encryption
     --cert-path PATH              Path to TLS certificate file
     --key-path PATH               Path to TLS private key file
     --config PATH                 Path to configuration file
     --help                        Show help message and exit

Environment Variables
---------------------

.. list-table::
   :header-rows: 1
   :widths: 25 60 15

   * - Variable
     - Description
     - Default
   * - ``PASSWORD``
     - Overrides configured plaintext password
     - ``None``
   * - ``PASSWORD_HASH``
     - Overrides configured password with pre-hashed value
     - ``None``
   * - ``PADRELAY_LOG_DIR``
     - Directory where log files are written
     - ``./logs``
   * - ``PADRELAY_DEBUG``
     - Enable debug logging (``1``, ``true``, ``yes``, ``on``)
     - ``false``

TLS/SSL Configuration
---------------------

TLS is enabled by default for TCP connections in version 1.1.0+.

Certificate Management
~~~~~~~~~~~~~~~~~~~~~~

PadRelay automatically generates self-signed certificates if none are provided:

* **Location:** ``~/.padrelay/certs/`` (``%USERPROFILE%\.padrelay\certs\`` on Windows)
* **Files:** ``server.crt`` and ``server.key``
* **Validity:** 365 days

Custom Certificates
~~~~~~~~~~~~~~~~~~~

To use custom certificates:

.. code-block:: bash

   padrelay-server --cert-path /path/to/cert.pem --key-path /path/to/key.pem

Or in configuration:

.. code-block:: ini

   [server]
   cert_path = /path/to/cert.pem
   key_path = /path/to/key.pem

Disabling TLS
~~~~~~~~~~~~~

.. warning::
   Disabling TLS is not recommended. Only disable on trusted networks.

.. code-block:: bash

   padrelay-server --disable-tls
   padrelay-client --disable-tls

Password Security
-----------------

Password Hashing
~~~~~~~~~~~~~~~~

On first run, the server automatically converts plaintext passwords to PBKDF2 hashes:

**Before:**

.. code-block:: ini

   [server]
   password = my_password

**After:**

.. code-block:: ini

   [server]
   password = pbkdf2_sha256$100000$abc123...$def456...

Pre-Hashing Passwords
~~~~~~~~~~~~~~~~~~~~~

Generate a password hash beforehand:

.. code-block:: python

   from padrelay.security.auth import Authenticator
   print(Authenticator.hash_password('my_password'))

Then use in configuration or ``PASSWORD_HASH`` environment variable.

Password Strength
~~~~~~~~~~~~~~~~~

PadRelay warns about weak passwords but does not enforce requirements. Recommendations:

* Minimum 12 characters
* Mix of uppercase, lowercase, numbers, symbols
* Avoid common passwords
* Use a password manager

Example Configuration Files
---------------------------

Minimal TCP Setup
~~~~~~~~~~~~~~~~~

**Server:**

.. code-block:: ini

   [server]
   host = 0.0.0.0
   port = 9999
   protocol = tcp
   password = your_secure_password

   [vgamepad]
   type = xbox360

**Client:**

.. code-block:: ini

   [network]
   server_ip = 192.168.1.100
   server_port = 9999
   protocol = tcp
   password = your_secure_password

   [joystick]
   index = 0

UDP Low-Latency Setup
~~~~~~~~~~~~~~~~~~~~~~

**Server:**

.. code-block:: ini

   [server]
   host = 0.0.0.0
   port = 9999
   protocol = udp
   password = your_secure_password
   max_requests = 6000

   [vgamepad]
   type = xbox360

**Client:**

.. code-block:: ini

   [network]
   server_ip = 192.168.1.100
   server_port = 9999
   protocol = udp
   password = your_secure_password

   [client]
   update_rate = 120

Custom Controller Mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   [server]
   host = 0.0.0.0
   port = 9999
   protocol = tcp
   password = your_secure_password

   [vgamepad]
   type = ds4

   [button_mapping_ds4]
   0 = DS4_BUTTON_CROSS
   1 = DS4_BUTTON_CIRCLE
   2 = DS4_BUTTON_SQUARE
   3 = DS4_BUTTON_TRIANGLE

   [axis_mapping]
   left_stick_x = 0
   left_stick_y = 1
   right_stick_x = 2
   right_stick_y = 3

   [axis_options]
   dead_zone = 0.15
   invert_left_y = true

See Also
--------

* :doc:`quickstart` - Getting started guide
* :doc:`user_guide/key_mapper` - Creating custom mappings
* :doc:`user_guide/tls_setup` - TLS/SSL setup guide
* :doc:`security` - Security best practices
