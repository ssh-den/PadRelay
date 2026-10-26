Troubleshooting
===============

Collect the first error on each peer, not just the final reconnect message.
Check package versions in the same Python environments as the running commands:

.. code-block:: bash

   python -m pip show padrelay
   python --version

The CLI has no ``--version`` flag. Enable ``PADRELAY_DEBUG=1`` before startup;
logs default to ``~/.padrelay/logs/padrelay.log`` or the directory selected by
``PADRELAY_LOG_DIR``. Remove credentials and private material before sharing
logs or INI files. See :doc:`../contributing` for bug-report details.

Connection Refused or Timeout
-----------------------------

* Confirm the server reached its listening state. TLS identity or gamepad
  initialization can fail before the listener exists.
* Check ``host``, ``port`` and the client's destination. The server default
  ``127.0.0.1`` cannot accept remote clients. ``0.0.0.0`` is a bind address,
  not a client destination.
* Allow TCP for TCP mode, and **TCP plus UDP on the same port** for UDP v2.
  A successful TCP connection in UDP mode does not prove UDP input is allowed.
* Check that both peers select the same transport and support the new protocol.

For a Windows server, ``Get-NetTCPConnection -LocalPort 9999`` and
``Get-NetUDPEndpoint -LocalPort 9999`` can show the listeners. Replace the port
as needed. Ping tests IP reachability, not TLS, authentication or UDP delivery.

Certificate or TLS Failure
--------------------------

For verification errors, check the trusted certificate/CA bundle, expiry,
system date and expected SAN name. The default self-signed identity reached by
LAN IP needs its trusted certificate copy plus ``server_hostname = localhost``.
``server_hostname`` does not change where the client connects.

If the server reports an incomplete or mismatched identity, supply both valid
custom paths or restore the complete default pair. It deliberately does not
regenerate over one remaining file. Renewal of a self-signed identity also
requires updating the clients' trust copies. See :doc:`tls_setup`.

An SSL wrong-version error often means a TLS client reached a plaintext TCP
listener or another service. Check the selected port and settings; do not
bypass certificate checks as a diagnostic shortcut. UDP does not permit
``--disable-tls`` even over a VPN.

Authentication Rejected
------------------------

Verify one matching credential source on each side. Client ``password_hash``
overrides plaintext credentials, while server environment selection has its
own precedence; see :doc:`../configuration`. Two independently generated
hashes of the same password have different salts and are not interchangeable
as pre-hashed client credentials. Copy the server's exact hash or use the
original plaintext password on the client.

Invalid or excessive PBKDF2 parameters are rejected before hashing. Regenerate
stored hashes outside 100000–600000 iterations or with unsupported salt sizes.
UDP requires credentials supplied before startup; it does not prompt for them.

Admission Rejected or Input Dropped
-----------------------------------

One pending or authenticated client is allowed per server. Stop an old client
before opening another. Pending authentication has a five-second deadline;
repeated login attempts also consume the separate per-IP and global budgets.

UDP rate limits aggregate by IP across ports. An INI copied from TCP with
``max_requests = 100`` can quickly exhaust at 60 Hz; use an appropriate UDP
budget, normally 6000 per 60 seconds for the default rate. At 120 Hz the
sustained input rate alone is 7200 per minute. Global and storage limits still
apply. Wait for budgets to refill and reduce traffic rather than rotating ports.

UDP has no token/clock-skew negotiation. Upgrade legacy peers, keep TLS control
open, and check that UDP reaches the server. Wrong-session, expired, replayed,
stale or forged packets are silently dropped. Scheduled session expiry after
ten minutes causes reconnection with a fresh key. Use TCP if reliable delivery
is preferable on the current network.

Controller or Output Failure
----------------------------

Select the correct ``--joystick-index`` on both client and mapper. An unknown
device needs a client JSON profile; a mismatched profile stops capture. The
client automatically reconnects only a unique matching device identity. When
multiple identical devices are present, explicitly select one and restart.

Use ``joy.cpl`` to distinguish a missing virtual device from incorrect input.
Windows output still requires the ``server`` extra and ViGEmBus. Remove legacy
server mapping sections and regenerate a client profile for protocol 2.0.
Hat inputs are normalized on the client; DS4 D-pad and PS use special output
APIs. Touchpad, gyro and feedback forwarding are not implemented.

Latency or High CPU
-------------------

Start with 60 Hz and compare wired/network load and CPU use on both peers.
Higher polling rates increase packet and driver work; they do not establish a
latency guarantee. UDP avoids retransmitting stale input but still has TLS
control, encryption and admission costs. Adjust its packet budget with the
polling rate and measure before attributing a delay to the transport alone.
