Quick Start Guide
=================

This guide will get you up and running with PadRelay in minutes.

Prerequisites
-------------

Before you begin, ensure you have:

* PadRelay installed on both client and server machines (see :doc:`installation`)
* ViGEmBus driver installed on the Windows server
* A physical gamepad connected to the client machine
* Both machines on the same network (or connected via VPN)

Basic Setup
-----------

Step 1: Create Configuration Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PadRelay uses INI configuration files. Example files are provided in the ``config/`` directory.

**Server Configuration** (``server_config.ini``):

.. code-block:: ini

   [server]
   host = 0.0.0.0
   port = 9999
   protocol = tcp
   password = your_secure_password_here
   rate_limit_window = 60
   max_requests = 100
   block_duration = 2

   [vgamepad]
   type = xbox360

**Client Configuration** (``client_config.ini``):

.. code-block:: ini

   [network]
   server_ip = 192.168.1.100
   server_port = 9999
   protocol = tcp
   password = your_secure_password_here

   [joystick]
   index = 0

   [client]
   update_rate = 60

.. important::
   Replace ``192.168.1.100`` with your server's actual IP address and
   choose a strong password. The server will automatically hash the password
   on first run.

Step 2: Start the Server
~~~~~~~~~~~~~~~~~~~~~~~~~

On your Windows machine, start the server:

.. code-block:: bash

   padrelay-server --config server_config.ini

You should see output similar to:

.. code-block:: text

   2025-01-06 10:30:00 [INFO] Server started on 0.0.0.0:9999 (TCP)
   2025-01-06 10:30:00 [INFO] TLS/SSL enabled
   2025-01-06 10:30:00 [INFO] Virtual gamepad type: xbox360
   2025-01-06 10:30:00 [INFO] Waiting for client connections...

.. note::
   TLS is enabled by default in version 1.1.0+. To disable it (not recommended),
   use the ``--disable-tls`` flag.

Step 3: Start the Client
~~~~~~~~~~~~~~~~~~~~~~~~~

On your client machine (with the physical gamepad), start the client:

.. code-block:: bash

   padrelay-client --config client_config.ini

You should see:

.. code-block:: text

   2025-01-06 10:30:05 [INFO] Gamepad detected: Xbox 360 Controller
   2025-01-06 10:30:05 [INFO] Connecting to 192.168.1.100:9999 (TCP)
   2025-01-06 10:30:05 [INFO] TLS/SSL enabled
   2025-01-06 10:30:05 [INFO] Connected to server
   2025-01-06 10:30:05 [INFO] Authentication successful
   2025-01-06 10:30:05 [INFO] Forwarding gamepad input...

Step 4: Test the Connection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Press buttons on your physical gamepad
2. The server should log input reception
3. On Windows, open "Set up USB game controllers" (``joy.cpl``)
4. You should see a virtual Xbox 360 or DualShock 4 controller
5. Open the controller properties and test that inputs are working

Using Command-Line Arguments
-----------------------------

Instead of configuration files, you can use command-line arguments:

Server Example:

.. code-block:: bash

   padrelay-server --host 0.0.0.0 --port 9999 --protocol tcp --password mypass --gamepad-type xbox360

Client Example:

.. code-block:: bash

   padrelay-client --server-ip 192.168.1.100 --server-port 9999 --protocol tcp --password mypass

.. tip::
   Command-line arguments override configuration file settings.

Using UDP for Lower Latency
----------------------------

For gaming with lower latency requirements, use UDP:

**Server:**

.. code-block:: ini

   [server]
   protocol = udp
   max_requests = 6000  # Higher limit for UDP

**Client:**

.. code-block:: ini

   [network]
   protocol = udp

.. warning::
   UDP does not support TLS encryption. Use UDP only on trusted networks
   or within a VPN tunnel.

Environment Variables
---------------------

For security, you can provide passwords via environment variables:

.. code-block:: bash

   # Linux/macOS
   export PASSWORD="your_secure_password"
   padrelay-server --config server_config.ini

   # Windows PowerShell
   $env:PASSWORD="your_secure_password"
   padrelay-server --config server_config.ini

   # Windows Command Prompt
   set PASSWORD=your_secure_password
   padrelay-server --config server_config.ini

Pre-Hashed Passwords
~~~~~~~~~~~~~~~~~~~~

For extra security, use pre-hashed passwords:

.. code-block:: bash

   # Generate hash (run once)
   python -c "from padrelay.security.auth import Authenticator; print(Authenticator.hash_password('your_password'))"

   # Use the output in your config or environment
   export PASSWORD_HASH="pbkdf2_sha256$100000$abc123...$def456..."

Mapping Custom Controllers
---------------------------

If your controller doesn't work correctly with default mappings, use the key mapper:

.. code-block:: bash

   padrelay-keymapper --output my_controller.ini

Follow the on-screen instructions to map each button and axis. Then use the generated file:

.. code-block:: bash

   padrelay-server --config my_controller.ini
   padrelay-client --config my_controller.ini

See :doc:`user_guide/key_mapper` for detailed instructions.

Running from Source
-------------------

If you installed from source, you can run the scripts directly:

.. code-block:: bash

   # Server
   python -m padrelay.scripts.server --config server_config.ini

   # Client
   python -m padrelay.scripts.client --config client_config.ini

   # Or use the scripts directly
   python scripts/server.py --config server_config.ini
   python scripts/client.py --config client_config.ini

Common Issues
-------------

"Failed to initialize gamepad"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** No gamepad detected or wrong index.

**Solution:**

1. Ensure gamepad is connected
2. Try a different joystick index: ``--joystick-index 1``
3. Test with ``pygame`` to verify detection

"Connection refused"
~~~~~~~~~~~~~~~~~~~~

**Cause:** Server not running or firewall blocking.

**Solution:**

1. Verify server is running
2. Check firewall settings
3. Verify IP address and port are correct
4. Test with ``telnet <server-ip> 9999``

"Authentication failed"
~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Password mismatch.

**Solution:**

1. Ensure passwords match on client and server
2. Check for typos in configuration files
3. Try resetting the password in config

"TLS handshake failed"
~~~~~~~~~~~~~~~~~~~~~~

**Cause:** TLS certificate issues.

**Solution:**

1. Check that both client and server have TLS enabled/disabled consistently
2. Verify certificate paths (server)
3. Check system time is synchronized
4. For self-signed certificates, ensure they're not expired

Enable debug logging for more details:

.. code-block:: bash

   export PADRELAY_DEBUG=1
   padrelay-server --config server_config.ini

See :doc:`user_guide/troubleshooting` for more solutions.

Next Steps
----------

* Read the :doc:`configuration` guide for all available options
* Learn about :doc:`security` best practices
* Explore :doc:`user_guide/tls_setup` for secure connections
* Check the :doc:`architecture` for how PadRelay works internally
