Protocol
========

The JSON/control version is ``1.0``. UDP uses envelope version ``2`` with magic
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
     "protocol_version": "1.0",
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

   {"type": "auth_response", "protocol_version": "1.0", "response": "<64 hex characters>"}

The server compares the response with ``hmac.compare_digest`` and replies with
``auth_success`` or ``auth_failed``, each with ``protocol_version: "1.0"``.
Malformed or failed authentication closes the connection. An ``error`` reply
may contain a human-readable ``message`` when admission is denied; it has no
numeric error-code contract. CLI server mode requires a password.

For UDP, ``auth_success`` additionally contains:

.. code-block:: json

   {
     "type": "auth_success",
     "protocol_version": "1.0",
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

The client sends the current state, not a list of button events:

.. code-block:: json

   {
     "type": "input",
     "protocol_version": "1.0",
     "buttons": [true, false, true],
     "axes": [0.0, -0.5, 0.8, 0.0],
     "hats": [[0, 1]],
     "triggers": [0.0, 0.7]
   }

* ``buttons`` is a boolean array indexed by physical button number.
* ``axes`` contains numbers in [-1, 1]; ``triggers`` contains numbers in [0, 1].
* ``hats`` contains integer pairs with coordinates -1, 0 or 1. Hats are carried
  and validated, but the current gamepad handler does not apply them to output.

Absent arrays default to empty during validation. Send complete state arrays
to avoid retaining previous output unintentionally. ``timestamp`` may be present
but is not required or used for authentication. The TCP client omits it from
most updates. Unknown fields have no defined effect.

TCP carries this JSON directly after authentication. UDP encrypts it in the
envelope below. Input is validated before gamepad processing; invalid input is
discarded, not clamped. UDP also checks ``protocol_version`` on each input.
TCP checks it during authentication, not in the input validator.

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
``protocol_version: "1.0"``. A heartbeat response has a five-second deadline;
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
