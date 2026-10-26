API Reference
=============

This page provides detailed API documentation for PadRelay's modules and classes. The documentation is automatically generated from source code docstrings.

Client Module
-------------

Client Application
~~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.client.client_app
   :members:
   :undoc-members:
   :show-inheritance:

Input Handling
~~~~~~~~~~~~~~

.. automodule:: padrelay.client.input
   :members:
   :undoc-members:
   :show-inheritance:

Client Constants
~~~~~~~~~~~~~~~~

.. automodule:: padrelay.client.constants
   :members:
   :undoc-members:

Server Module
-------------

Server Application
~~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.server.server_app
   :members:
   :undoc-members:
   :show-inheritance:

Input Processor
~~~~~~~~~~~~~~~

.. automodule:: padrelay.server.input_processor
   :members:
   :undoc-members:
   :show-inheritance:

Virtual Gamepad
~~~~~~~~~~~~~~~

.. automodule:: padrelay.server.virtual_gamepad
   :members:
   :undoc-members:
   :show-inheritance:

Server Constants
~~~~~~~~~~~~~~~~

.. automodule:: padrelay.server.constants
   :members:
   :undoc-members:

Protocol Module
---------------

TCP Protocol
~~~~~~~~~~~~

.. automodule:: padrelay.protocol.tcp
   :members:
   :undoc-members:
   :show-inheritance:

UDP Protocol
~~~~~~~~~~~~

.. automodule:: padrelay.protocol.udp
   :members:
   :undoc-members:
   :show-inheritance:

Messages
~~~~~~~~

.. automodule:: padrelay.protocol.messages
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: from_dict

Protocol Constants
~~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.protocol.constants
   :members:
   :undoc-members:

Security Module
---------------

Authentication
~~~~~~~~~~~~~~

.. automodule:: padrelay.security.auth
   :members:
   :undoc-members:
   :show-inheritance:

Rate Limiting
~~~~~~~~~~~~~

.. automodule:: padrelay.security.rate_limiting
   :members:
   :undoc-members:
   :show-inheritance:

TLS Utilities
~~~~~~~~~~~~~

.. automodule:: padrelay.security.tls_utils
   :members:
   :undoc-members:
   :show-inheritance:

Password Strength
~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.security.password_strength
   :members:
   :undoc-members:

Core Module
-----------

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
   :show-inheritance:

Logging Utilities
~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.core.logging_utils
   :members:
   :undoc-members:

Scripts Module
--------------

Server Entry Point
~~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.scripts.server
   :members:
   :undoc-members:

Client Entry Point
~~~~~~~~~~~~~~~~~~

.. automodule:: padrelay.scripts.client
   :members:
   :undoc-members:

Key Mapper
~~~~~~~~~~

.. automodule:: padrelay.scripts.key_mapper
   :members:
   :undoc-members:

Usage Examples
--------------

Creating a Client Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from padrelay.client.client_app import VirtualGamepadClient
   from padrelay.client.input import GamepadInput

   async def main():
       # Initialize gamepad
       gamepad = GamepadInput(joystick_index=0)
       if not gamepad.initialize():
           print("Failed to initialize gamepad")
           return

       # Create client
       client = VirtualGamepadClient(
           server_ip="192.168.1.100",
           server_port=9999,
           protocol="tcp",
           gamepad=gamepad,
           update_rate=60,
           password="my_password",
           enable_tls=True
       )

       # Run client
       await client.run()

   if __name__ == "__main__":
       asyncio.run(main())

Creating a Server Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from padrelay.server.server_app import VirtualGamepadServer

   async def main():
       # Create server
       server = VirtualGamepadServer(
           host="0.0.0.0",
           port=9999,
           password="my_password",
           gamepad_type="xbox360",
           protocol="tcp",
           enable_tls=True
       )

       # Run server
       await server.run()

   if __name__ == "__main__":
       asyncio.run(main())

Using the Authenticator
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from padrelay.security.auth import Authenticator

   # Hash a password
   password_hash = Authenticator.hash_password("my_password")
   print(password_hash)
   # Output: pbkdf2_sha256$100000$abc123...$def456...

   # Create authenticator with plaintext password
   auth1 = Authenticator(password="my_password")

   # Create authenticator with hashed password
   auth2 = Authenticator(password=password_hash)

   # Generate challenge
   challenge = auth1.generate_challenge()

   # Compute response
   response = auth2.compute_response(challenge, auth1.salt, auth1.iterations)

   # Verify response
   is_valid = auth1.verify_response(challenge, response)
   print(is_valid)  # True

Custom Message Creation
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from padrelay.protocol.messages import InputMessage

   # Create input message
   msg = InputMessage(
       buttons=[0, 1, 4],  # Buttons A, B, and LB pressed
       axes=[0.0, -0.5, 0.8, 0.0],  # Left stick up, right stick right
       hats=[[0, 0]],  # D-pad centered
       triggers={"left": 0.0, "right": 0.7}  # Right trigger pressed
   )

   # Serialize to JSON
   json_str = msg.to_json()

   # Serialize to bytes
   data = msg.to_bytes()

Rate Limiting Example
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from padrelay.security.rate_limiting import RateLimiter

   # Create rate limiter (100 requests per 60 seconds)
   limiter = RateLimiter(
       max_requests=100,
       window_seconds=60,
       block_duration=120
   )

   # Check if client is allowed
   client_addr = "192.168.1.50"
   if limiter.is_allowed(client_addr):
       # Process request
       pass
   else:
       # Reject request
       print("Rate limit exceeded")

TLS Certificate Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from padrelay.security.tls_utils import generate_self_signed_cert

   # Generate certificate
   cert_path = Path("server.crt")
   key_path = Path("server.key")

   generate_self_signed_cert(
       cert_path=cert_path,
       key_path=key_path,
       hostname="localhost",
       days=365
   )

   print(f"Certificate created: {cert_path}")
   print(f"Private key created: {key_path}")

See Also
--------

* :doc:`architecture` - System architecture overview
* :doc:`protocol` - Protocol specification
* :doc:`security` - Security implementation details
