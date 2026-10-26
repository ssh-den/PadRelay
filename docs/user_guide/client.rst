Client
======

The client polls a physical controller through pygame and sends its state to
one server. Start with :doc:`../quickstart`; all flags and INI keys are listed
once in :doc:`../configuration`.

Controller Selection
--------------------

``--joystick-index`` selects a pygame device, defaulting to zero. To inspect
the device indices in the client's Python environment:

.. code-block:: python

   import pygame

   pygame.init()
   pygame.joystick.init()
   for index in range(pygame.joystick.get_count()):
       device = pygame.joystick.Joystick(index)
       device.init()
       print(index, device.get_name())
   pygame.quit()

The index is used for initial selection. After disconnection the client searches
for the recorded GUID/name/platform/input counts, rather than reusing that index.
An ambiguous match among identical devices is never selected automatically.
Startup without a connected device waits for the selected index to appear.

Automatic Mapping and Profiles
-------------------------------

SDL GameController supplies logical button/stick/trigger meanings for supported
devices. Recognition uses SDL support, not the device display name or axis count.
Unknown devices require a client JSON profile from :doc:`key_mapper`.
``--controller-profile`` or ``[joystick] profile`` selects that profile, which
overrides SDL capture completely. There is one normalization path per device.

Only canonical logical state crosses the network. Physical data, calibration
and profiles remain on the client. Both peers must support protocol 2.0.

Transport and Update Rate
-------------------------

TCP is the default and delivers an ordered stream over TLS. UDP v2 drops lost
or stale input rather than retransmitting it, and encrypts each input datagram.
It still needs a live verified TLS control connection to the same server port.
Both peers must select the same mode. See :doc:`tls_setup` for trust settings.

``--update-rate`` or ``[client] update_rate`` controls polling, defaulting to
60 Hz. Either transport accepts a higher rate; 120 Hz does not require UDP.
The setting is a requested rate, not a latency guarantee. Increase it only
after checking CPU, packet loss and the server's UDP budgets. For example,
120 Hz needs 7200 packets per minute before headroom, beyond the default
per-IP UDP refill of 6000 per minute.

Reconnect and Shutdown
----------------------

Connection failures normally retry after a fixed five seconds until shutdown.
Heartbeat runs over TCP/TLS in either mode. UDP sessions expire after 600 seconds
and reconnect with fresh keys; losing control invalidates the old data session.
Trust errors never cause a plaintext retry.

A failed controller read closes the network session so the server resets held
input. The client waits for a matching physical controller and reopens it automatically.
If multiple matching devices are present, explicitly select one and restart.

Use ``Ctrl+C`` to stop. Shutdown cancels pending connection/retry waits and
allows at most one second for graceful stream closure before aborting it.

A single server admits one client. To use another physical controller, run a
separate client and server process on another port; each server creates its
own virtual gamepad. Do not expect several clients to share one listener.

Diagnostics
-----------

Logs default to ``~/.padrelay/logs/padrelay.log``. Set ``PADRELAY_LOG_DIR`` to
change the directory and ``PADRELAY_DEBUG=1`` before startup for diagnostics.
Use :doc:`troubleshooting` for connection and input failures. Python embedding
examples and constructor differences are in :doc:`../api`; there is no public
``send_input`` override hook.
