Client Guide
============

This guide covers everything you need to know about running and configuring the PadRelay client.

Overview
--------

The PadRelay client captures input from a physical gamepad and transmits it to the server over the network. The client can run on any operating system that supports Python and pygame.

Basic Usage
-----------

Starting the Client
~~~~~~~~~~~~~~~~~~~

Using a configuration file:

.. code-block:: bash

   padrelay-client --config client_config.ini

Using command-line arguments:

.. code-block:: bash

   padrelay-client --server-ip 192.168.1.100 --server-port 9999 --password mypass

Stopping the Client
~~~~~~~~~~~~~~~~~~~

Press ``Ctrl+C`` to gracefully stop the client. The client will:

1. Close the connection to the server
2. Release the gamepad
3. Clean up resources
4. Exit

Configuration
-------------

Configuration File
~~~~~~~~~~~~~~~~~~

Create a file (e.g., ``client_config.ini``):

.. code-block:: ini

   [network]
   server_ip = 192.168.1.100
   server_port = 9999
   protocol = tcp
   password = your_secure_password

   [joystick]
   index = 0

   [client]
   update_rate = 60

Command-Line Options
~~~~~~~~~~~~~~~~~~~~

All settings can be overridden via command-line:

.. code-block:: bash

   padrelay-client \
     --server-ip 192.168.1.100 \
     --server-port 9999 \
     --protocol tcp \
     --password mypass \
     --joystick-index 0 \
     --update-rate 60 \
     --enable-tls

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Set password via environment variable:

.. code-block:: bash

   # Linux/macOS
   export PASSWORD="your_secure_password"
   padrelay-client --config client_config.ini

   # Windows PowerShell
   $env:PASSWORD="your_secure_password"
   padrelay-client --config client_config.ini

Gamepad Detection
-----------------

Listing Available Gamepads
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The client automatically detects connected gamepads. To see which gamepads are available:

.. code-block:: python

   import pygame
   pygame.init()
   pygame.joystick.init()

   print(f"Found {pygame.joystick.get_count()} gamepad(s)")
   for i in range(pygame.joystick.get_count()):
       joystick = pygame.joystick.Joystick(i)
       joystick.init()
       print(f"  [{i}] {joystick.get_name()}")

Selecting a Gamepad
~~~~~~~~~~~~~~~~~~~

Use the ``joystick_index`` setting to select which gamepad to use:

.. code-block:: ini

   [joystick]
   index = 0  # First gamepad

Or via command-line:

.. code-block:: bash

   padrelay-client --joystick-index 1  # Second gamepad

Multiple Gamepads
~~~~~~~~~~~~~~~~~

To use multiple gamepads simultaneously, run multiple client instances:

.. code-block:: bash

   # Terminal 1: First gamepad
   padrelay-client --joystick-index 0 --server-port 9999

   # Terminal 2: Second gamepad (different server or port)
   padrelay-client --joystick-index 1 --server-port 9998

Update Rate
-----------

The update rate controls how often input is sent to the server:

.. code-block:: ini

   [client]
   update_rate = 60  # 60 Hz = 16.7ms between updates

Choosing an Update Rate
~~~~~~~~~~~~~~~~~~~~~~~~

* **60 Hz (default):** Good balance of responsiveness and bandwidth
* **30 Hz:** Lower bandwidth, acceptable for most games
* **120 Hz:** Maximum responsiveness for competitive gaming (requires UDP)

.. note::
   Higher update rates use more bandwidth and CPU. For most games, 60 Hz is sufficient.

Bandwidth Usage
~~~~~~~~~~~~~~~

Approximate bandwidth at different rates:

* 30 Hz: ~7.5 KB/s (~0.06 Mbps)
* 60 Hz: ~15 KB/s (~0.12 Mbps)
* 120 Hz: ~30 KB/s (~0.24 Mbps)

Protocol Selection
------------------

TCP vs UDP
~~~~~~~~~~

**TCP (Default)**

**Pros:**
- Reliable data delivery  
- Supports TLS encryption  
- Automatically reconnects if the connection drops  

**Cons:**
- Higher latency (approximately 10–30 ms)  
- Slightly more bandwidth overhead  

**UDP**

**Pros:**
- Lower latency (approximately 1–5 ms)  
- Less bandwidth usage  

**Cons:**
- No built-in encryption (use VPN if needed)  
- Occasional packet loss or unreliable delivery

When to Use TCP
~~~~~~~~~~~~~~~

* Default choice for most scenarios
* When security is important
* When reliability is more important than latency
* Over unreliable networks (Wi-Fi, VPN)

When to Use UDP
~~~~~~~~~~~~~~~

* Competitive gaming requiring lowest latency
* Stable, low-latency network (wired LAN)
* Already using VPN for security
* Willing to accept occasional input loss

Switching Protocols
~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   [network]
   protocol = udp  # Change from tcp to udp

.. warning::
   Both client and server must use the same protocol!

TLS Configuration
-----------------

TLS is enabled by default for TCP connections. See :doc:`tls_setup` for details.

Enable TLS
~~~~~~~~~~

.. code-block:: bash

   padrelay-client --enable-tls  # Explicitly enable (default)

Disable TLS
~~~~~~~~~~~

.. code-block:: bash

   padrelay-client --disable-tls  # Not recommended

.. warning::
   Only disable TLS on trusted networks or when using VPN/SSH tunnel.

Automatic Reconnection
----------------------

The client automatically reconnects if the connection is lost:

* **Retry Interval:** 5 seconds
* **Infinite Retries:** Client keeps trying until successful
* **Exponential Backoff:** Not currently implemented

Reconnection Scenarios
~~~~~~~~~~~~~~~~~~~~~~

* Server restart
* Network interruption
* Rate limit block (after block duration)

Manual Reconnection
~~~~~~~~~~~~~~~~~~~

If automatic reconnection fails, restart the client:

.. code-block:: bash

   # Stop with Ctrl+C, then restart
   padrelay-client --config client_config.ini

Logging
-------

Log Location
~~~~~~~~~~~~

Logs are written to:

* Linux/macOS: ``./logs/padrelay.log``
* Windows: ``.\logs\padrelay.log``

Custom log directory:

.. code-block:: bash

   export PADRELAY_LOG_DIR=/var/log/padrelay
   padrelay-client --config client_config.ini

Log Levels
~~~~~~~~~~

* **INFO:** Normal operation (default)
* **WARNING:** Potential issues
* **ERROR:** Errors that don't stop the client
* **DEBUG:** Detailed diagnostic information

Enable Debug Logging
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   export PADRELAY_DEBUG=1
   padrelay-client --config client_config.ini

Debug logs include:

* Connection details
* Authentication flow
* TLS handshake information
* Input state (not logged by default)

Troubleshooting
---------------

Gamepad Not Detected
~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Failed to initialize gamepad. Exiting.

**Solutions:**

1. Verify gamepad is connected
2. Check gamepad works in other applications
3. Try different USB port
4. Install gamepad drivers
5. Run gamepad detection script (see above)

Connection Refused
~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Connection refused to 192.168.1.100:9999

**Solutions:**

1. Verify server is running
2. Check firewall settings
3. Verify IP address is correct
4. Test with ``telnet 192.168.1.100 9999``

Authentication Failed
~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Authentication failed

**Solutions:**

1. Verify password matches server
2. Check for typos in configuration
3. Try resetting password in config
4. Check server logs for details

TLS Handshake Failed
~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: TLS handshake failed

**Solutions:**

1. Ensure server has TLS enabled
2. Check certificate validity
3. Verify system time is correct
4. Try disabling TLS temporarily to test

High Latency
~~~~~~~~~~~~

**Symptoms:**

* Delayed input response
* Laggy controls

**Solutions:**

1. Switch to UDP protocol
2. Check network latency with ``ping``
3. Use wired connection instead of Wi-Fi
4. Reduce update rate if network is saturated
5. Close bandwidth-intensive applications

Input Not Working
~~~~~~~~~~~~~~~~~

**Symptoms:**

* Client connects but inputs don't work
* Some buttons work, others don't

**Solutions:**

1. Verify controller mapping on server
2. Use key mapper to create custom mapping
3. Test gamepad in pygame
4. Check server logs for errors

See :doc:`troubleshooting` for more solutions.

Advanced Usage
--------------

Running from Python
~~~~~~~~~~~~~~~~~~~

You can import and run the client programmatically:

.. code-block:: python

   import asyncio
   from padrelay.client.client_app import VirtualGamepadClient
   from padrelay.client.input import GamepadInput

   async def main():
       gamepad = GamepadInput(joystick_index=0)
       if not gamepad.initialize():
           print("Failed to initialize gamepad")
           return

       client = VirtualGamepadClient(
           server_ip="192.168.1.100",
           server_port=9999,
           protocol="tcp",
           gamepad=gamepad,
           update_rate=60,
           password="mypass",
           enable_tls=True
       )

       await client.run()

   asyncio.run(main())

Custom Input Processing
~~~~~~~~~~~~~~~~~~~~~~~

You can subclass ``VirtualGamepadClient`` to add custom input processing:

.. code-block:: python

   from padrelay.client.client_app import VirtualGamepadClient

   class CustomClient(VirtualGamepadClient):
       async def send_input(self):
           # Custom input processing before sending
           await super().send_input()

Running as a Service
~~~~~~~~~~~~~~~~~~~~

To run the client as a systemd service on Linux:

1. Create service file ``/etc/systemd/system/padrelay-client.service``:

.. code-block:: ini

   [Unit]
   Description=PadRelay Client
   After=network.target

   [Service]
   Type=simple
   User=yourusername
   WorkingDirectory=/home/yourusername
   ExecStart=/usr/local/bin/padrelay-client --config /etc/padrelay/client_config.ini
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target

2. Enable and start service:

.. code-block:: bash

   sudo systemctl enable padrelay-client
   sudo systemctl start padrelay-client
   sudo systemctl status padrelay-client

See Also
--------

* :doc:`../quickstart` - Quick start guide
* :doc:`../configuration` - Configuration reference
* :doc:`tls_setup` - TLS setup guide
* :doc:`troubleshooting` - Troubleshooting guide
