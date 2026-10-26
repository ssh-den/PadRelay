Troubleshooting Guide
=====================

This guide helps you diagnose and fix common issues with PadRelay.

General Troubleshooting Steps
------------------------------

Before diving into specific issues:

1. **Check logs:** Review logs in ``logs/padrelay.log``
2. **Enable debug mode:** Set ``PADRELAY_DEBUG=1`` for detailed logging
3. **Verify versions:** Ensure client and server use compatible versions
4. **Test connectivity:** Use ``ping`` and ``telnet`` to test network
5. **Check firewall:** Verify firewall allows connections

Connection Issues
-----------------

Connection Refused
~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Connection refused to 192.168.1.100:9999

**Causes:**

* Server not running
* Wrong IP address or port
* Firewall blocking connection
* Server bound to wrong interface

**Solutions:**

1. Verify server is running:

   .. code-block:: bash

      # Check if process is running
      ps aux | grep padrelay-server  # Linux/Mac
      tasklist | findstr python      # Windows

2. Verify server IP and port:

   .. code-block:: bash

      netstat -an | grep 9999        # Linux/Mac
      netstat -an | findstr 9999     # Windows

3. Test with telnet:

   .. code-block:: bash

      telnet 192.168.1.100 9999

4. Check firewall:

   .. code-block:: bash

      # Linux
      sudo ufw status
      sudo ufw allow 9999/tcp

      # Windows
      # Open Windows Firewall and allow Python or port 9999

5. Verify server binding:

   .. code-block:: ini

      [server]
      host = 0.0.0.0  # Accept connections from all interfaces

Connection Timeout
~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Connection timeout

**Solutions:**

* Check network connectivity with ``ping``
* Verify no intermediate firewalls blocking
* Try increasing timeout (not currently configurable)
* Check server is responsive (not hung)

Connection Drops
~~~~~~~~~~~~~~~~

**Symptoms:**

* Connection established but drops after a few seconds
* Intermittent disconnections

**Solutions:**

1. Check rate limiting settings (may be too strict)
2. Verify network stability
3. Check heartbeat settings (TCP only)
4. Review logs for errors before disconnect
5. Try using TCP instead of UDP

Authentication Issues
---------------------

Authentication Failed
~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Authentication failed

**Causes:**

* Password mismatch
* Incorrect password hash
* Hash parameter mismatch (salt/iterations)

**Solutions:**

1. Verify passwords match exactly:

   .. code-block:: bash

      # Server config
      [server]
      password = my_password

      # Client config
      [network]
      password = my_password

2. Reset password to plaintext on both sides
3. Delete hashed password from server config and restart
4. Use environment variable to override:

   .. code-block:: bash

      export PASSWORD="my_password"

5. Check for trailing spaces or special characters

Invalid Token (UDP)
~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   WARNING: Invalid authentication token

**Solutions:**

1. Synchronize system clocks (must be within 60 seconds)
2. Request auth parameters from server first
3. Verify password matches
4. Check network isn't modifying packets

Gamepad Issues
--------------

Gamepad Not Detected
~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Failed to initialize gamepad

**Solutions:**

1. List available gamepads:

   .. code-block:: python

      import pygame
      pygame.init()
      pygame.joystick.init()
      print(f"Gamepads found: {pygame.joystick.get_count()}")

2. Try different joystick index:

   .. code-block:: bash

      padrelay-client --joystick-index 1

3. Test gamepad in other applications
4. Check USB connection
5. Install gamepad drivers
6. Try different USB port

Buttons Not Working
~~~~~~~~~~~~~~~~~~~

**Symptoms:**

* Some buttons don't respond
* Buttons mapped incorrectly

**Solutions:**

1. Use key mapper to create custom mapping:

   .. code-block:: bash

      padrelay-keymapper --output my_mapping.ini

2. Manually check button indices in pygame
3. Verify button mapping in server config
4. Test gamepad in Windows game controller settings (``joy.cpl``)

Axes Inverted or Wrong
~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

* Pushing up moves stick down
* Left/right reversed

**Solutions:**

1. Invert axes in config:

   .. code-block:: ini

      [axis_options]
      invert_left_y = true
      invert_right_y = true

2. Remap axes with key mapper
3. Adjust dead zone if stick drifting:

   .. code-block:: ini

      [axis_options]
      dead_zone = 0.15

Virtual Gamepad Issues
----------------------

Virtual Gamepad Not Appearing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

* No virtual gamepad in Windows game controller settings
* Server starts but no gamepad visible

**Solutions:**

1. Verify ViGEmBus is installed:

   * Open Device Manager
   * Look for "Nefarius Virtual Gamepad Emulation Bus"

2. Reinstall ViGEmBus:

   * Download from https://github.com/ViGEm/ViGEmBus/releases
   * Run installer as administrator
   * Restart computer

3. Check vgamepad import:

   .. code-block:: python

      import vgamepad
      gamepad = vgamepad.VX360Gamepad()  # Should not raise error

4. Run server as administrator (sometimes needed)

5. Check server logs for vgamepad errors

Gamepad Input Lag
~~~~~~~~~~~~~~~~~

**Symptoms:**

* Noticeable delay between physical and virtual input

**Solutions:**

1. Use UDP protocol for lower latency
2. Increase update rate:

   .. code-block:: ini

      [client]
      update_rate = 120

3. Use wired connection instead of Wi-Fi
4. Reduce network latency:

   .. code-block:: bash

      ping 192.168.1.100  # Should be <10ms

5. Close bandwidth-intensive applications
6. Check CPU usage on both machines

TLS/SSL Issues
--------------

TLS Handshake Failed
~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: TLS handshake failed
   ERROR: SSL: WRONG_VERSION_NUMBER

**Solutions:**

1. Ensure TLS setting matches on client and server:

   .. code-block:: bash

      # Both enabled
      padrelay-server --enable-tls
      padrelay-client --enable-tls

      # Or both disabled
      padrelay-server --disable-tls
      padrelay-client --disable-tls

2. Check certificate validity:

   .. code-block:: bash

      openssl x509 -in ~/.padrelay/certs/server.crt -noout -dates

3. Synchronize system clocks
4. Update Python and OpenSSL:

   .. code-block:: bash

      pip install --upgrade cryptography

5. Regenerate certificates:

   .. code-block:: bash

      rm ~/.padrelay/certs/server.*
      # Restart server to generate new certificates

Certificate Errors
~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Certificate file not found
   ERROR: Permission denied reading certificate

**Solutions:**

1. Let PadRelay auto-generate certificates (remove custom cert paths)
2. Fix permissions:

   .. code-block:: bash

      chmod 600 ~/.padrelay/certs/server.key
      chmod 644 ~/.padrelay/certs/server.crt

3. Verify certificate files exist
4. Check paths in configuration are correct

Performance Issues
------------------

High CPU Usage
~~~~~~~~~~~~~~

**Causes:**

* Update rate too high
* Inefficient input processing
* Too many clients connected

**Solutions:**

1. Reduce update rate:

   .. code-block:: ini

      [client]
      update_rate = 30  # Lower from 60

2. Close unnecessary applications
3. Use UDP instead of TCP
4. Check for busy loops in logs

High Bandwidth Usage
~~~~~~~~~~~~~~~~~~~~

**Solutions:**

1. Reduce update rate
2. Use UDP (less overhead than TCP)
3. Disconnect unused clients
4. Check for message flooding in logs

Rate Limiting Issues
--------------------

Rate Limit Exceeded
~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Rate limit exceeded, connection blocked

**Causes:**

* Update rate higher than server allows
* Multiple clients from same IP
* Rate limit settings too strict

**Solutions:**

1. Increase server rate limits:

   .. code-block:: ini

      [server]
      max_requests = 200      # For TCP
      max_requests = 12000    # For UDP

2. Reduce client update rate
3. Wait for block duration to expire
4. Use different client IP addresses

Protocol Issues
---------------

Protocol Version Mismatch
~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Protocol version mismatch

**Solutions:**

1. Update both client and server to same version:

   .. code-block:: bash

      pip install --upgrade padrelay

2. Check versions:

   .. code-block:: bash

      padrelay-client --version
      padrelay-server --version

UDP Packet Loss
~~~~~~~~~~~~~~~

**Symptoms:**

* Intermittent input drops
* Occasional missing inputs

**Solutions:**

1. Switch to TCP for reliability
2. Improve network quality (use wired connection)
3. Reduce network congestion
4. Lower update rate to reduce packet rate

Installation Issues
-------------------

vgamepad Installation Fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**

.. code-block:: text

   ERROR: Failed building wheel for vgamepad

**Solutions:**

1. Ensure using Windows (vgamepad requires Windows)
2. Install Visual C++ Build Tools
3. Update pip:

   .. code-block:: bash

      python -m pip install --upgrade pip

4. Install pre-built wheel if available

pygame Installation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Linux:**

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install python3-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
   pip install pygame

**macOS:**

.. code-block:: bash

   brew install sdl2 sdl2_image sdl2_ttf sdl2_mixer
   pip install pygame

**Windows:**

Usually works without issues. If not:

.. code-block:: bash

   pip install pygame --upgrade

Debug Mode
----------

Enabling Debug Logging
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Linux/macOS
   export PADRELAY_DEBUG=1
   padrelay-server --config server_config.ini

   # Windows PowerShell
   $env:PADRELAY_DEBUG="1"
   padrelay-server --config server_config.ini

   # Windows Command Prompt
   set PADRELAY_DEBUG=1
   padrelay-server --config server_config.ini

What Debug Mode Shows
~~~~~~~~~~~~~~~~~~~~~

* SSL/TLS handshake details
* Authentication challenge/response
* Connection state changes
* Message parsing and validation
* Certificate information
* Detailed error traces

Reading Debug Logs
~~~~~~~~~~~~~~~~~~~

Look for:

* **ERROR:** Critical failures
* **WARNING:** Potential issues
* **DEBUG:** Detailed diagnostic info
* **Stack traces:** For exceptions

Common Log Messages
-------------------

Understanding Warnings
~~~~~~~~~~~~~~~~~~~~~~

**"Password is weak"**

* Not critical, but consider using stronger password
* See password strength recommendations

**"Configuration file is world-readable"**

* Security risk if file contains passwords
* Fix with: ``chmod 600 config.ini``

**"Certificate expires in X days"**

* Renew certificate soon
* Auto-generated certificates valid 365 days

Understanding Errors
~~~~~~~~~~~~~~~~~~~~

**"Rate limit exceeded"**

* Client sending too many requests
* Increase rate limits or reduce update rate

**"Invalid message format"**

* Corrupt message or protocol mismatch
* Check versions match
* Check network isn't corrupting packets

**"Failed to create virtual gamepad"**

* ViGEmBus not installed or not working
* Reinstall ViGEmBus
* Run as administrator

Getting Help
------------

Before Asking for Help
~~~~~~~~~~~~~~~~~~~~~~~

1. Check this troubleshooting guide
2. Review logs with debug mode enabled
3. Search existing GitHub issues
4. Verify using latest version

Reporting Issues
~~~~~~~~~~~~~~~~

When reporting issues, include:

1. **PadRelay version:** ``padrelay-client --version``
2. **Operating systems:** Client and server OS
3. **Python version:** ``python --version``
4. **Configuration:** Sanitized config files (remove passwords)
5. **Logs:** Relevant log excerpts with debug enabled
6. **Steps to reproduce:** How to trigger the issue
7. **Expected behavior:** What should happen
8. **Actual behavior:** What actually happens

Where to Get Help
~~~~~~~~~~~~~~~~~

* **GitHub Issues:** https://github.com/ssh-den/PadRelay/issues
* **Documentation:** https://padrelay.readthedocs.io
* **Email:** sshden@duck.com (for security issues)

See Also
--------

* :doc:`client` - Client configuration guide
* :doc:`server` - Server configuration guide
* :doc:`tls_setup` - TLS/SSL setup
* :doc:`../security` - Security considerations
