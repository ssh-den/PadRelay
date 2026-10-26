Protocol
========

The JSON/control version is ``2.0``. UDP uses envelope version ``2`` with magic
``PRU2``. There is no version negotiation or fallback to legacy UDP tokens.

TCP Framing
-----------

Each message is a UTF-8 JSON object preceded by its payload length as an unsigned
four-byte big-endian integer. The receiver rejects payloads larger than
**4096 bytes**; the prefix is not part of that limit. TLS wraps this stream by
default in the CLI.

UDP mode opens a verified TLS control connection to the same numeric TCP port
as the UDP data port. Authentication and heartbeat use TCP framing in both modes.

Authentication
--------------

After the TLS handshake, the server reserves a connection slot and sends:

.. code-block:: json

   {
     "type": "auth_challenge",
     "protocol_version": "2.0",
     "challenge": "0123456789abcdef0123456789abcdef",
     "salt": "0123456789abcdef0123456789abcdef",
     "iterations": 100000
   }

The challenge contains 16 random bytes encoded as 32 hex characters. The client
checks the protocol version and PBKDF2 bounds before deriving a key. These are
the actual byte encodings used by the implementation:

.. code-block:: python

   digest_hex = hashlib.pbkdf2_hmac(
       "sha256", password.encode(), salt.encode(), iterations
   ).hex()
   response = hmac.new(
       digest_hex.encode(), challenge.encode(), hashlib.sha256
   ).hexdigest()

The salt and challenge are encoded as text, not decoded from hex. A client
configured with a stored hash uses its digest directly; it must have the same
hash as the server. The response is:

.. code-block:: json

   {"type": "auth_response", "protocol_version": "2.0", "response": "<64 hex characters>"}

The server compares the response with ``hmac.compare_digest`` and replies with
``auth_success`` or ``auth_failed``, each with ``protocol_version: "2.0"``.
Malformed or failed authentication closes the connection. An ``error`` reply
may contain a human-readable ``message`` when admission is denied; it has no
numeric error-code contract. CLI server mode requires a password.

For UDP, ``auth_success`` additionally contains:

.. code-block:: json

   {
     "type": "auth_success",
     "protocol_version": "2.0",
     "udp_session": {
       "version": 2,
       "session_id": "<32 hex characters>",
       "key": "<64 hex characters>"
     }
   }

The server generates a new random ID and AES-256-GCM key for each admitted
control connection. This material is sent only inside TLS.

Input
-----

Each input packet is exactly one complete logical snapshot. There are no raw
physical indices, hat arrays, duplicated controller blocks or per-frame timestamps.
Unknown/missing fields, legacy arrays and incompatible versions are rejected.

.. code-block:: json

   {
     "type": "input",
     "protocol_version": "2.0",
     "buttons": {
       "a": false,
       "b": false,
       "x": false,
       "y": false,
       "lb": false,
       "rb": false,
       "view": false,
       "menu": false,
       "guide": false,
       "left_stick": false,
       "right_stick": false,
       "dpad_up": false,
       "dpad_down": false,
       "dpad_left": false,
       "dpad_right": false
     },
     "axes": {
       "left_x": 0.0,
       "left_y": 0.0,
       "right_x": 0.0,
       "right_y": 0.0
     },
     "triggers": {
       "left": 0.0,
       "right": 0.0
     }
   }

Buttons have boolean values and the exact logical names shown above. Axes are
finite numbers in [-1, 1], with positive Y meaning up. Triggers are finite
numbers in [0, 1], with zero released. Booleans are not numeric axis values.
Every field is required, including neutral values, so omissions cannot retain
old output. Calibration and physical mapping happen only on the client.

Input and control use version 2.0. Both peers must be upgraded together; there
is no legacy input fallback. UDP envelope version 2 is unchanged. Input is
validated before output processing in both transports. TCP sends this JSON
after authentication; UDP encrypts it in the envelope below. Server output is
reset on disconnect or after ``server.input_timeout`` seconds without valid
input (default 1.0), even while heartbeat remains alive. The watchdog checks
every 50 milliseconds. Unchanged valid snapshots refresh the input deadline.

UDP Envelope
------------

.. list-table::
   :header-rows: 1

   * - Bytes
     - Field
   * - 0–3
     - ``PRU2``
   * - 4–19
     - Session ID, 16 raw bytes
   * - 20–27
     - Unsigned 64-bit big-endian sequence
   * - 28 onward
     - AES-256-GCM ciphertext followed by its 16-byte tag

The complete 28-byte header is associated data. The nonce is the sequence
encoded as a 12-byte big-endian integer. One client sends with each key;
sequences start at zero and sending stops before ``2**32``. The full datagram
must fit in **4096 bytes**, leaving at most 4052 bytes for the JSON plaintext.

The server requires a live session bound to the control peer's IP. Source-port
changes do not create a new identity. Replay state is a 64-bit bitmap updated
only after AEAD verification. Duplicate packets and packets outside its window
are rejected; older reordered input is not applied even if first seen.

Sessions expire after 600 seconds and are revoked when control disconnects.
The client reconnects to get a fresh key. The server does not answer UDP
datagrams: legacy JSON, parameter requests, unknown sessions, expired sessions
and forged packets are dropped without replies or per-packet error reporting.

Heartbeat and Lifecycle
-----------------------

The client sends ``heartbeat`` over the TCP/TLS stream, starting after login,
then at 30-second intervals. The server responds with ``heartbeat_ack`` and
``protocol_version: "2.0"``. A heartbeat response has a five-second deadline;
the server waits at most 35 seconds for its next stream message.

TLS handshake and server authentication each have a five-second deadline.
UDP clients additionally bound control connection establishment to ten seconds.
After a connection failure the client normally retries after a fixed five
seconds, until shutdown. There is no exponential backoff.

The server defaults to one pending or authenticated client. Slot release and
UDP session revocation occur on failure, timeout, cancellation and disconnect.
An authenticated client's disconnect resets the virtual gamepad.

Malformed TCP framing/JSON ends the read and closes the connection; the server
does not promise a structured error reply for every invalid packet. Unknown
post-authentication message types are ignored. For admission budgets and their
configuration, see :doc:`security` and :doc:`configuration`.
