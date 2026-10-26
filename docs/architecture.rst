Architecture
============

The client reads a physical controller through pygame. The server translates
received state into a virtual Xbox 360 or DualShock 4 gamepad through vgamepad.
One server process owns one virtual gamepad and admits one client by default.

Components
----------

.. list-table::
   :header-rows: 1

   * - Module
     - Responsibility
   * - ``client.input.GamepadInput``
     - Own device identity/lifecycle and normalize through SDL or a client profile.
   * - ``client.client_app.VirtualGamepadClient``
     - Connect, authenticate, send input, maintain heartbeat and reconnect.
   * - ``server.server_app.VirtualGamepadServer``
     - Own listeners, connection reservations, sessions and shutdown.
   * - ``server.input_processor.GamepadHandler``
     - Cache one immutable InputState and expire stale input.
   * - ``server.virtual_gamepad.VirtualGamepad``
     - Adapt logical state to Xbox/DS4 native output; isolate vgamepad/ViGEm.
   * - ``protocol``
     - JSON framing, input validation and UDP routing.
   * - ``security``
     - Password authentication, TLS contexts, UDP encryption and admission limits.
   * - ``core`` and ``scripts``
     - Configuration, logging and installed CLI entry points.

Input Path
----------

.. code-block:: text

   pygame -> GamepadInput -> VirtualGamepadClient
                                |
                   TCP/TLS input or UDP v2 datagrams
                                |
   VirtualGamepadServer -> validation -> GamepadHandler -> vgamepad

``core.controller_state.InputState`` is the one immutable logical state model.
The client normalizes the selected device using SDL or a device-bound JSON profile,
including calibration and thresholds. Only named logical controls are serialized.
The server caches one state and translates it through the virtual-output adapter.
No physical maps, raw arrays or duplicate input blocks are sent to the server.

Profiles are persisted atomically by ``client.controller_profile``. Runtime device
handles, identity and scan timing belong to ``GamepadInput``; there is no global
state store. A disconnect closes the network session and resets output. Reopening
matches device identity and refuses ambiguous selection. A separate input watchdog
resets stale state independently of heartbeat, including during UDP packet loss.
Failed native resets invalidate the state cache and are retried by the watchdog;
an exception does not terminate its background loop. Failed report writes also
invalidate the cache and schedule a reset, including before the first successful
input. A successful complete report clears the pending reset.
The adapter handles Xbox/DS4 coordinate conventions, DS4 D-pad and PS. Touchpad,
gyro and feedback forwarding are outside this input contract.

Connections
-----------

TCP uses length-prefixed JSON. The CLI enables verified TLS by default, then
authenticates the client with a password challenge. Input and heartbeat share
the stream. TLS can be explicitly disabled for TCP only.

UDP v2 has two channels on the same numeric port:

* A verified TLS/TCP control connection for login, session key delivery and
  heartbeat.
* One-way AES-256-GCM datagrams for input, with authenticated session IDs and
  sequence counters.

The control connection owns its UDP session. Closing control revokes the key;
after 600 seconds the client reconnects for a new session. Datagram loss is not
retransmitted, and old reordered state is not applied. Wire encodings and timing
are defined in :doc:`protocol`; trust setup is in :doc:`user_guide/tls_setup`.

Concurrency and Cleanup
-----------------------

Network work runs on asyncio event loops. Client heartbeat is a separate task;
password derivation is dispatched to a worker thread after parameter validation.
Server connection handlers reserve admission slots before asynchronous login
and release them in ``finally``. UDP callbacks perform bounded routing and
replay checks against the live session registry.

Shutdown closes pending and authenticated streams, revokes sessions, closes the
UDP transport and resets gamepad state. A rejected connection does not reset
the admitted client's output. IP/global rate budgets and their limitations are
described in :doc:`security`.

Configuration and Extension Points
----------------------------------

The entry points parse CLI, INI and credential environment variables, then
construct the application objects. Python constructors do not apply CLI
defaults: TCP ``enable_tls`` defaults to false at that API boundary. See
:doc:`configuration` for precedence and :doc:`api` for constructors.

Controller-specific changes normally belong in configuration. Protocol changes
must update both ends, message handling, validation and network tests. There is
no plugin API for macros or arbitrary transforms. See :doc:`development` for
the repository layout and checks.
