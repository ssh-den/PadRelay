Quick Start
===========

Install PadRelay on both machines using :doc:`installation`. The client needs a
physical gamepad; the Windows server needs vgamepad and ViGEmBus. This example
uses TCP/TLS on a LAN. Replace addresses and password placeholders before use.

Server
------

Create ``server.ini`` on the server:

.. code-block:: ini

   [server]
   host = 0.0.0.0
   port = 9999
   protocol = tcp
   password = replace-with-your-password

   [vgamepad]
   type = xbox360

``0.0.0.0`` listens on all interfaces; restrict inbound access with the firewall
or bind to the server's LAN address. The built-in default ``127.0.0.1`` accepts
only local clients. Allow TCP port 9999, then start:

.. code-block:: bash

   padrelay-server --config server.ini

The server may hash and rewrite the INI password. It also creates a default
self-signed certificate and key in ``%USERPROFILE%\.padrelay\certs\``.
Copy only ``server.crt`` to the client through a trusted channel; keep the key
on the server. Existing incomplete identities cause startup to fail rather
than being replaced.

Client
------

Create ``client.ini`` with the server's real address and the local path to the
trusted certificate copy:

.. code-block:: ini

   [network]
   server_ip = 192.168.1.100
   server_port = 9999
   protocol = tcp
   password = replace-with-your-password

   [joystick]
   index = 0

   [security]
   ca_path = /path/to/trusted-server.crt
   server_hostname = localhost

Use the same password as the server. ``localhost`` is the identity in the
auto-generated certificate; the connection still goes to ``server_ip``.
For custom certificates or a private CA, see :doc:`user_guide/tls_setup`.

.. code-block:: bash

   padrelay-client --config client.ini

Open ``joy.cpl`` on Windows and inspect the virtual controller's properties
while pressing buttons and moving sticks. If the device is present but its
layout is wrong, use :doc:`user_guide/key_mapper`. Stop each process with
``Ctrl+C``. Passwords may instead be supplied through environment variables;
their precedence is documented in :doc:`configuration`.

Switch to UDP v2
----------------

Set ``protocol = udp`` in both files and add ``max_requests = 6000`` under the
server's ``[server]`` section. If you copied the repository server template,
replace its explicit TCP value of 100; changing protocol alone does not change
that setting.

Keep the password and certificate trust settings. Allow **both TCP and UDP** on
port 9999: TCP/TLS owns login, key delivery and heartbeat; UDP carries encrypted
input. Update both endpoints together. Legacy UDP tokens and
``--disable-tls`` are rejected. Sessions reconnect after ten minutes with a new
key; the UDP data channel does not retransmit lost input.

For connection, certificate or input failures, use
:doc:`user_guide/troubleshooting`.
