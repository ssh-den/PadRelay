Configuration
=============

Pass an INI file with ``--config``; it is not loaded automatically. Templates
are in ``config/``. Relative file paths are resolved from the process working
directory, not from the INI file's directory. Use separate server and client
files: controller mappings are interpreted on the server.

Ordinary settings use CLI values, then INI values, then defaults. Credentials
have the special rules below. Numeric zero is currently treated as unspecified
while merging settings: for example, ``--joystick-index 0`` does not override a
nonzero index in the INI. Edit that INI value instead. Put comments on separate
lines; inline comments after values are not enabled by the parser.

Client Settings
---------------

.. list-table::
   :header-rows: 1

   * - INI section/key
     - CLI flag
     - Default and meaning
   * - ``network.server_ip``
     - ``--server-ip``
     - ``127.0.0.1``; connection address or hostname.
   * - ``network.server_port``
     - ``--server-port``
     - ``9999``; data port and, for UDP, TCP control port.
   * - ``network.protocol``
     - ``--protocol tcp|udp``
     - ``tcp``; must match the server.
   * - ``network.password``
     - ``--password``
     - No default; plaintext password or encoded PBKDF2 hash.
   * - ``network.password_hash``
     - ``--password-hash``
     - No default; takes precedence over plaintext credentials.
   * - ``joystick.index``
     - ``--joystick-index``
     - ``0``; pygame device index.
   * - ``client.update_rate``
     - ``--update-rate``
     - ``60``; input polls per second, for either transport.
   * - ``security.enable_tls``
     - ``--enable-tls`` / ``--disable-tls``
     - Enabled by default for TCP; mandatory for UDP control.
   * - ``security.ca_path``
     - ``--ca-path``
     - System trust store if omitted; CA bundle or trusted self-signed certificate.
   * - ``security.server_hostname``
     - ``--server-hostname``
     - ``server_ip``; expected certificate identity, independent of destination.

TCP prompts for a password when none is supplied. UDP does not prompt: provide
credentials through configuration, CLI or environment before starting it.
The client never rewrites its INI password.

Server Settings
---------------

.. list-table::
   :header-rows: 1

   * - INI section/key
     - CLI flag
     - Default and meaning
   * - ``server.host``
     - ``--host``
     - ``127.0.0.1``; use a LAN address or ``0.0.0.0`` for remote clients.
   * - ``server.port``
     - ``--port``
     - ``9999``; TCP port, plus UDP data port in UDP mode.
   * - ``server.protocol``
     - ``--protocol tcp|udp``
     - ``tcp``.
   * - ``server.password``
     - ``--password``
     - Required; plaintext or encoded PBKDF2 hash. There is no server ``--password-hash`` flag.
   * - ``server.rate_limit_window``
     - ``--rate-limit-window``
     - ``60`` seconds; UDP per-IP and global bucket refill period.
   * - ``server.max_requests``
     - ``--max-requests``
     - ``100`` for TCP, ``6000`` for UDP when not explicitly configured.
   * - ``server.block_duration``
     - ``--block-duration``
     - ``2`` seconds; block duration for exhausted UDP buckets.
   * - ``vgamepad.type``
     - ``--gamepad-type xbox360|ds4``
     - ``xbox360``; virtual device type.
   * - ``security.enable_tls``
     - ``--enable-tls`` / ``--disable-tls``
     - Enabled for TCP by default; cannot be disabled for UDP.
   * - ``security.cert_path``
     - ``--cert-path``
     - Default server certificate; custom certificate and key must be supplied together.
   * - ``security.key_path``
     - ``--key-path``
     - Default private key; custom paths must already contain a matching pair.

TCP prompts for missing credentials; UDP fails without them. Both CLI server
modes require a nonempty password. The default connection limit is one pending
or authenticated client; there is no CLI/INI option to raise it.

In UDP mode, ``max_requests`` is the per-IP token-bucket capacity, refilled over
``rate_limit_window``. It is not a TCP input-message limit. A separate login
budget uses ``min(max_requests, 10)`` attempts per IP per 60 seconds. Global UDP
capacity is 12000; login capacity is 1000. These global capacities and the 1024-IP
storage cap are not CLI options. Full semantics are in :doc:`security`.

An explicit INI ``max_requests = 100`` remains 100 after changing ``protocol``
to UDP. For 60 Hz, use 6000 or another budget above the sustained packet rate.
For 120 Hz, at least 7200 tokens per 60 seconds are needed before headroom;
increasing the per-IP setting does not raise the global capacity.

Credentials and Environment
---------------------------

.. list-table::
   :header-rows: 1

   * - Variable
     - Behavior
   * - ``PASSWORD``
     - Supplies a plaintext password or encoded hash at runtime.
   * - ``PASSWORD_HASH``
     - Supplies an encoded PBKDF2 credential.
   * - ``PADRELAY_LOG_DIR``
     - Log directory; default ``~/.padrelay/logs`` on all platforms.
   * - ``PADRELAY_DEBUG``
     - Enables debug logs for ``1``, ``true``, ``yes`` or ``on`` (case-insensitive).

Set only one credential form to avoid surprising precedence:

* On the client, any selected ``password_hash`` wins over ``password``.
  Environment variables replace the corresponding CLI/INI field; a configured
  hash can therefore still win over ``PASSWORD``.
* On the server, nonempty ``PASSWORD`` wins over ``PASSWORD_HASH``; either wins
  over CLI and INI credentials. The server does not read an INI ``password_hash``
  key: store an encoded hash in ``[server] password`` instead.
* A nonempty plaintext server INI password is hashed and written back only
  when selected for this run. CLI or environment credentials skip migration;
  empty INI passwords are not hashed. ConfigParser rewrites the file without
  preserving comments; write failures are logged.

To generate an encoded hash without placing the password in shell history:

.. code-block:: python

   from getpass import getpass
   from padrelay.security.auth import Authenticator

   print(Authenticator.hash_password(getpass("Password: ")))

Protect the output as a credential. A hash supplied to the client must be a copy
of the server's exact hash. Bounds are 100000–600000 iterations and 16–128 ASCII
salt characters. There is no INI iteration-count setting. Use valid generated
hashes, not abbreviated examples containing ellipses. In POSIX shell assignments,
single-quote a literal hash so its dollar signs are not expanded.

TLS Paths
---------

Default identity files are ``~/.padrelay/certs/server.crt`` and ``server.key``
(``%USERPROFILE%\.padrelay\certs\`` on Windows). With no custom paths, both
are generated only when both are absent. Incomplete, invalid or mismatched
identities stop startup. Trust and renewal instructions have one home:
:doc:`user_guide/tls_setup`.

Controller Mapping
------------------

Server mapping sections are ``[button_mapping_xbox360]`` or
``[button_mapping_ds4]``. Keys are physical button indices; values are constants
from ``vgamepad.XUSB_BUTTON`` or ``vgamepad.DS4_BUTTONS`` respectively.
A nonempty custom button map replaces the built-in map rather than extending it.

.. code-block:: ini

   [button_mapping_xbox360]
   0 = XUSB_GAMEPAD_B
   1 = XUSB_GAMEPAD_A

``[axis_mapping]`` accepts ``left_stick_x``, ``left_stick_y``, ``right_stick_x``,
``right_stick_y``, ``trigger_left`` and ``trigger_right`` as nonnegative physical
axis indices. These entries are interpreted only by the server.

.. code-block:: ini

   [axis_mapping]
   left_stick_x = 0
   left_stick_y = 1
   right_stick_x = 2
   right_stick_y = 3
   trigger_left = 4
   trigger_right = 5

With a nonempty axis map, only configured controls are applied: stick coordinates
need both X and Y, and omitted triggers have no fallback. Trigger axes in this
mode are converted from [-1, 1] to [0, 1]. With no axis map, the server uses axes
0/1 for the left stick, 2/3 for the right, and the message's ``triggers`` array.

``[axis_options]`` supports:

* ``dead_zone``: default ``0.1``; stick values whose absolute value is at or below
  this threshold become zero. This is a cutoff, not range rescaling.
* ``trigger_threshold``: default ``0.1``; lower trigger values become zero.
  The key mapper explicitly writes ``0.05``.
* ``invert_left_y`` and ``invert_right_y``: default ``false``; inversion is
  applied in the configured axis-mapping path, not the basic fallback path.

Hats and generated ``*_hat`` sections are not currently applied to virtual
output. The client does not load server mapping sections. For generating and
testing a map, see :doc:`user_guide/key_mapper`.

Use ``padrelay-client --help``, ``padrelay-server --help`` or
``padrelay-keymapper --help`` for the installed command's complete flag list.
