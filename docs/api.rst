API Reference
=============

Signatures and docstrings below are generated from the current source. The CLI
parses configuration and supplies defaults before constructing these objects;
Python callers must do that themselves. In particular, TCP constructors default
to ``enable_tls=False``: pass ``True`` explicitly for verified TLS. UDP
constructors require a password and force TLS control.

Applications embedding the client must initialize and clean up ``GamepadInput``
and manage ``run()`` / ``shutdown()``. There is no public ``send_input`` method.
For wire formats see :doc:`protocol`, not the message constructors alone.

Examples
--------

Password challenge-response with a plaintext client and hashed server:

.. code-block:: python

   from padrelay.security.auth import Authenticator

   server = Authenticator(Authenticator.hash_password("example-password"))
   client = Authenticator("example-password")
   client.set_parameters(server.salt, server.iterations)
   challenge = server.generate_tcp_challenge()
   response = client.generate_tcp_response(challenge)
   assert server.verify_tcp_response(challenge, response)

An input message serializes a complete canonical state:

.. code-block:: python

   import json
   from padrelay.core.controller_state import InputState
   from padrelay.protocol.messages import InputMessage, validate_input_message

   message = InputMessage(InputState(frozenset({"a", "dpad_up"}),
                                     left_y=0.5, trigger_right=0.7))
   assert validate_input_message(json.loads(message.to_json()))

Admission and request budgets use ``ConnectionTracker``; there is no separate
``RateLimiter`` class. Reservation and authentication counts are separate:

.. code-block:: python

   from padrelay.security.rate_limiting import ConnectionTracker

   tracker = ConnectionTracker(max_connections=1, max_requests=2)
   peer = ("192.0.2.1", 1234)
   assert tracker.reserve(peer)
   tracker.authenticate(peer)
   assert tracker.active_connections == 1
   assert not tracker.is_rate_limited(peer)
   tracker.disconnect(peer)

Use :doc:`user_guide/tls_setup` for certificate generation. Session parameters
are secret and may be transmitted only inside authenticated TLS; creating a
``UDPSession`` alone does not establish peer trust.

Client
------

Application
~~~~~~~~~~~

.. automodule:: padrelay.client.client_app
   :members:
   :undoc-members:

Input
~~~~~

.. automodule:: padrelay.client.input
   :members:
   :undoc-members:

Constants
~~~~~~~~~

.. automodule:: padrelay.client.constants
   :members:
   :undoc-members:

Controller Profiles
~~~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.client.controller_profile
   :members:

Server
------

Application
~~~~~~~~~~~

.. automodule:: padrelay.server.server_app
   :members:
   :undoc-members:

Input Processing
~~~~~~~~~~~~~~~~

.. automodule:: padrelay.server.input_processor
   :members:
   :undoc-members:

Virtual Gamepad
~~~~~~~~~~~~~~~

.. automodule:: padrelay.server.virtual_gamepad
   :members:
   :undoc-members:

Constants
~~~~~~~~~

.. automodule:: padrelay.server.constants
   :members:
   :undoc-members:

Protocol
--------

TCP
~~~

.. automodule:: padrelay.protocol.tcp
   :members:
   :undoc-members:

UDP
~~~

.. automodule:: padrelay.protocol.udp
   :members:
   :undoc-members:

Messages
~~~~~~~~

.. automodule:: padrelay.protocol.messages
   :members:
   :undoc-members:

Constants
~~~~~~~~~

.. automodule:: padrelay.protocol.constants
   :members:
   :undoc-members:

Security
--------

Authentication
~~~~~~~~~~~~~~

.. automodule:: padrelay.security.auth
   :members:
   :undoc-members:

UDP Sessions
~~~~~~~~~~~~

.. automodule:: padrelay.security.udp_session
   :members:
   :undoc-members:

Admission Limits
~~~~~~~~~~~~~~~~

.. automodule:: padrelay.security.rate_limiting
   :members:
   :undoc-members:

TLS
~~~

.. automodule:: padrelay.security.tls_utils
   :members:
   :undoc-members:

Password Warnings
~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.security.password_strength
   :members:
   :undoc-members:

Core
----

Controller State
~~~~~~~~~~~~~~~~

.. automodule:: padrelay.core.controller_state
   :members:

Configuration
~~~~~~~~~~~~~

.. automodule:: padrelay.core.config
   :members:
   :undoc-members:

Exceptions
~~~~~~~~~~

.. automodule:: padrelay.core.exceptions
   :members:
   :undoc-members:

Logging
~~~~~~~

.. automodule:: padrelay.core.logging_utils
   :members:
   :undoc-members:

Entry Points
------------

Client
~~~~~~

.. automodule:: padrelay.scripts.client
   :members:
   :undoc-members:

Server
~~~~~~

.. automodule:: padrelay.scripts.server
   :members:
   :undoc-members:

Key Mapper
~~~~~~~~~~

.. automodule:: padrelay.scripts.key_mapper
   :members:
   :undoc-members:
