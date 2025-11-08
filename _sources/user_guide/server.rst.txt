Server Guide
============

This guide covers running and configuring the PadRelay server on Windows.

Overview
--------

The PadRelay server receives gamepad input from clients and creates a virtual Xbox 360 or DualShock 4 controller using the ViGEmBus driver.

Requirements
------------

* Windows operating system
* ViGEmBus driver installed
* Python 3.6+ with vgamepad library
* Network connectivity to clients

Basic Usage
-----------

Starting the Server
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   padrelay-server --config server_config.ini

Or with command-line arguments:

.. code-block:: bash

   padrelay-server --host 0.0.0.0 --port 9999 --password mypass --gamepad-type xbox360

Stopping the Server
~~~~~~~~~~~~~~~~~~~

Press ``Ctrl+C`` to stop. The server will:

1. Close all client connections
2. Release virtual gamepad
3. Clean up resources

Configuration
-------------

Basic Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   [server]
   host = 0.0.0.0
   port = 9999
   protocol = tcp
   password = your_secure_password
   rate_limit_window = 60
   max_requests = 100
   block_duration = 2

   [vgamepad]
   type = xbox360

Virtual Gamepad Types
---------------------

Xbox 360 Controller
~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   [vgamepad]
   type = xbox360

Most compatible option. Supported by virtually all PC games.

DualShock 4 Controller
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   [vgamepad]
   type = ds4

Use for PlayStation-specific games or when you need touchpad/gyro features (not currently supported by PadRelay).

Verifying Virtual Gamepad
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Press ``Windows + R``
2. Type ``joy.cpl`` and press Enter
3. Virtual controller should appear in the list
4. Select controller and click "Properties" to test inputs

Network Configuration
---------------------

Binding Address
~~~~~~~~~~~~~~~

**Localhost only:**

.. code-block:: ini

   [server]
   host = 127.0.0.1  # Only accepts connections from same machine

**All interfaces:**

.. code-block:: ini

   [server]
   host = 0.0.0.0  # Accepts connections from any network interface

**Specific interface:**

.. code-block:: ini

   [server]
   host = 192.168.1.100  # Only on specific IP address

Port Selection
~~~~~~~~~~~~~~

Default port is 9999. Choose a different port if needed:

.. code-block:: ini

   [server]
   port = 12345

.. note::
   Make sure to update firewall rules and client configuration if changing the port.

Firewall Configuration
----------------------

Windows Firewall
~~~~~~~~~~~~~~~~

Allow PadRelay through Windows Firewall:

.. code-block:: powershell

   # Run as Administrator
   New-NetFirewallRule -DisplayName "PadRelay Server" -Direction Inbound -Program "C:\Path\To\Python\python.exe" -Action Allow

Or manually:

1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Click "Change settings" → "Allow another app"
4. Browse to python.exe and add it

Third-Party Firewalls
~~~~~~~~~~~~~~~~~~~~~

Configure your firewall to allow:

* **Protocol:** TCP or UDP (depending on configuration)
* **Port:** 9999 (or your configured port)
* **Program:** python.exe or padrelay-server.exe

Rate Limiting
-------------

Rate limiting prevents abuse and DoS attacks:

.. code-block:: ini

   [server]
   rate_limit_window = 60    # Time window in seconds
   max_requests = 100        # Max requests per window (TCP)
   block_duration = 2        # Block duration in seconds

UDP Rate Limits
~~~~~~~~~~~~~~~

UDP requires higher limits due to higher message rate:

.. code-block:: ini

   [server]
   protocol = udp
   max_requests = 6000  # 100 messages/second at 60 Hz

Adjusting Rate Limits
~~~~~~~~~~~~~~~~~~~~~

Increase for higher update rates:

.. code-block:: ini

   # For 120 Hz update rate
   max_requests = 200        # TCP
   max_requests = 12000      # UDP

Button and Axis Mapping
-----------------------

Custom Button Mappings
~~~~~~~~~~~~~~~~~~~~~~

Map physical button indices to virtual buttons:

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

Use the key mapper tool to generate mappings automatically (see :doc:`key_mapper`).

Custom Axis Mappings
~~~~~~~~~~~~~~~~~~~~

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

.. code-block:: ini

   [axis_options]
   dead_zone = 0.1            # Ignore movements below this threshold
   trigger_threshold = 0.1    # Trigger sensitivity
   invert_left_y = false      # Invert left stick Y axis
   invert_right_y = false     # Invert right stick Y axis

Password Management
-------------------

Automatic Hashing
~~~~~~~~~~~~~~~~~

The server automatically hashes plaintext passwords on first run:

**Before first run:**

.. code-block:: ini

   [server]
   password = my_password

**After first run:**

.. code-block:: ini

   [server]
   password = pbkdf2_sha256$100000$abc123...$def456...

Pre-Hashing Passwords
~~~~~~~~~~~~~~~~~~~~~

Generate hash before storing:

.. code-block:: python

   from padrelay.security.auth import Authenticator
   print(Authenticator.hash_password('my_password'))

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Provide password at runtime without storing in config:

.. code-block:: powershell

   # PowerShell
   $env:PASSWORD="my_secure_password"
   padrelay-server --config server_config.ini

.. code-block:: cmd

   REM Command Prompt
   set PASSWORD=my_secure_password
   padrelay-server --config server_config.ini

TLS/SSL Configuration
---------------------

TLS is enabled by default. See :doc:`tls_setup` for detailed setup.

Using Auto-Generated Certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The server automatically generates self-signed certificates in ``%USERPROFILE%\.padrelay\certs\``.

Using Custom Certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   padrelay-server --cert-path C:\path\to\cert.pem --key-path C:\path\to\key.pem

Multiple Clients
----------------

The server can handle multiple clients simultaneously:

* **TCP:** One connection per client
* **UDP:** Unlimited clients (shares port)

.. note::
   Only one client's input is processed at a time. The server uses input from the most recently active client.

Logging
-------

Logs are written to ``%USERPROFILE%\.padrelay\logs\padrelay.log`` by default.

Debug Logging
~~~~~~~~~~~~~

.. code-block:: powershell

   $env:PADRELAY_DEBUG="1"
   padrelay-server --config server_config.ini

Log Rotation
~~~~~~~~~~~~

Logs are automatically rotated:

* Max size: 1 MB per file
* Kept backups: 3 files

Troubleshooting
---------------

Virtual Gamepad Not Appearing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Verify ViGEmBus is installed (check Device Manager)
2. Restart the ViGEmBus driver service
3. Check for vgamepad import errors in logs
4. Reinstall ViGEmBus

Port Already in Use
~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ERROR: Address already in use

**Solutions:**

1. Stop other applications using the port
2. Use a different port: ``--port 9998``
3. Find and kill process: ``netstat -ano | findstr :9999``

Authentication Failures
~~~~~~~~~~~~~~~~~~~~~~~

Check server logs for client authentication attempts and verify passwords match.

Performance Issues
~~~~~~~~~~~~~~~~~~

If experiencing lag or dropped inputs:

1. Close unnecessary applications
2. Check CPU usage
3. Use UDP protocol
4. Reduce client update rate
5. Check network latency

Running as Windows Service
--------------------------

To run the server as a Windows service:

1. Install NSSM (Non-Sucking Service Manager)
2. Run as administrator:

.. code-block:: cmd

   nssm install PadRelayServer "C:\Path\To\python.exe" "C:\Path\To\Scripts\padrelay-server.exe --config C:\path\to\server_config.ini"
   nssm start PadRelayServer

See Also
--------

* :doc:`../configuration` - Configuration reference
* :doc:`key_mapper` - Creating custom mappings
* :doc:`tls_setup` - TLS/SSL setup
* :doc:`troubleshooting` - Troubleshooting guide
