Server
======

The server creates one virtual Xbox 360 or DualShock 4 gamepad and applies one
client's input. Install vgamepad and the Windows ViGEmBus driver as described
in :doc:`../installation`. Use :doc:`../quickstart` for a complete first run.

Listener and Firewall
----------------------

``--host`` or ``[server] host`` defaults to ``127.0.0.1``. Use the server's LAN
address to bind that interface, or ``0.0.0.0`` for all IPv4 interfaces. Clients
connect to a reachable server address, not ``0.0.0.0``.

The default port is 9999. In TCP mode allow inbound TCP on that port. In UDP v2
allow **both TCP and UDP** on it: TLS control is required even if a VPN is in
use. Restrict the rule's source addresses or network profile where possible.

The CLI requires a password in either mode. Credential selection and server
INI migration are described in :doc:`../configuration`; certificate trust and
custom identity paths are in :doc:`tls_setup`. Custom paths go in ``[security]``,
not ``[server]``.

Admission and Packet Budgets
----------------------------

Only one pending or authenticated connection is admitted per server process,
for both transports. An idle login attempt occupies that slot until it closes
or reaches the authentication deadline. Rejected clients do not take over the
gamepad. There is no CLI switch for multiple clients or automatic selection of
the most recently active client.

For UDP, ``max_requests`` sets per-IP bucket capacity, refilled over
``rate_limit_window``. CLI defaults are 6000 and 60 seconds. If the INI already
sets 100 for TCP, update that value when switching to UDP. Peers behind a NAT
share an IP budget; changing source port does not bypass it.

There are separate fixed global/storage ceilings and a capped authentication
budget. Raising ``max_requests`` does not remove them or increase TCP input
throughput. For exact limits and scope, see :doc:`../security`.

Gamepad Output
--------------

Choose ``xbox360`` or ``ds4`` with ``--gamepad-type`` or ``[vgamepad] type``.
DS4 mode does not forward touchpad, gyro, rumble or other feedback features.
Open ``joy.cpl`` to check that the virtual device exists and receives input.

Physical profiles and calibration live on the client; see :doc:`key_mapper`.
The server accepts only protocol-2 logical state. The adapter supports D-pad
diagonals/neutral and DS4 PS through the native special-button API.
``[server] input_timeout`` resets stale input independently of heartbeat; default
1.0 seconds, checked every 50 milliseconds.

Lifecycle and Logs
------------------

The server retains pending streams so shutdown can close them as well as
authenticated ones. Disconnecting an authenticated client revokes its UDP
session and resets gamepad state. ``Ctrl+C`` initiates shutdown.

Logs default to ``%USERPROFILE%\.padrelay\logs\padrelay.log`` on Windows.
``PADRELAY_DEBUG=1`` enables diagnostics; ``PADRELAY_LOG_DIR`` changes the
directory. File logging rotates at 1 MiB with three backups. For startup,
connection or driver errors, see :doc:`troubleshooting`.
