Protocol Specification
======================

This document describes the PadRelay network protocol in detail.

Protocol Overview
-----------------

PadRelay uses a JSON-based protocol for communication between clients and servers. The protocol supports both TCP and UDP transports with different authentication mechanisms.

Protocol Version
~~~~~~~~~~~~~~~~

Current version: **1.0**

The protocol version is included in every message and checked during connection establishment.

Transport Layers
----------------

TCP Transport
~~~~~~~~~~~~~

**Characteristics:**

* Reliable, ordered delivery
* Connection-oriented
* Supports TLS/SSL encryption
* Challenge-response authentication
* Heartbeat mechanism for keep-alive

**Use Cases:**

* Secure connections over untrusted networks
* When reliability is more important than latency
* Initial setup and testing

UDP Transport
~~~~~~~~~~~~~

**Characteristics:**

* Unreliable, unordered delivery
* Connectionless
* No TLS support (use VPN for security)
* Token-based authentication per message
* Lower latency than TCP

**Use Cases:**

* Gaming with low latency requirements
* Trusted local networks
* High-frequency input updates

Message Format
--------------

Base Message Structure
~~~~~~~~~~~~~~~~~~~~~~

All messages share a common base structure:

.. code-block:: json

   {
     "type": "message_type",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456"
   }

**Fields:**

* ``type`` (string): Message type identifier
* ``protocol_version`` (string): Protocol version (currently "1.0")
* ``timestamp`` (string): ISO 8601 timestamp when message was created

Message Types
-------------

Input Message
~~~~~~~~~~~~~

Transmits gamepad state from client to server.

**Type:** ``input``

**Direction:** Client → Server

**Format:**

.. code-block:: json

   {
     "type": "input",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "buttons": [0, 1, 4, 7],
     "axes": [0.0, -0.5, 0.8, 0.0],
     "hats": [[0, 1]],
     "triggers": {
       "left": 0.0,
       "right": 0.7
     },
     "token": "hmac_token_hex"
   }

**Fields:**

* ``buttons`` (array of integers): Indices of currently pressed buttons
* ``axes`` (array of floats): Axis positions, range -1.0 to 1.0
* ``hats`` (array of [x, y] pairs): D-pad positions, each -1, 0, or 1
* ``triggers`` (object, optional): Left and right trigger values, 0.0 to 1.0
* ``token`` (string, UDP only): HMAC authentication token

Authentication Messages
~~~~~~~~~~~~~~~~~~~~~~~

Challenge Message
^^^^^^^^^^^^^^^^^

Server initiates authentication by sending a challenge.

**Type:** ``auth_challenge``

**Direction:** Server → Client (TCP only)

**Format:**

.. code-block:: json

   {
     "type": "auth_challenge",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "challenge": "deadbeef1234567890abcdef",
     "salt": "abc123def456",
     "iterations": 100000
   }

**Fields:**

* ``challenge`` (string): Random hex-encoded bytes for HMAC computation
* ``salt`` (string): Salt for password hashing
* ``iterations`` (integer): PBKDF2 iteration count

Response Message
^^^^^^^^^^^^^^^^

Client responds to challenge with computed HMAC.

**Type:** ``auth_response``

**Direction:** Client → Server (TCP only)

**Format:**

.. code-block:: json

   {
     "type": "auth_response",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "response": "hmac_hex_value"
   }

**Fields:**

* ``response`` (string): HMAC-SHA256 of challenge using password-derived key

Success Message
^^^^^^^^^^^^^^^

Server confirms successful authentication.

**Type:** ``auth_success``

**Direction:** Server → Client

**Format:**

.. code-block:: json

   {
     "type": "auth_success",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456"
   }

Failed Message
^^^^^^^^^^^^^^

Server rejects authentication.

**Type:** ``auth_failed``

**Direction:** Server → Client

**Format:**

.. code-block:: json

   {
     "type": "auth_failed",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "reason": "Invalid credentials"
   }

**Fields:**

* ``reason`` (string, optional): Human-readable failure reason

Parameters Request
^^^^^^^^^^^^^^^^^^

Client requests authentication parameters (UDP only).

**Type:** ``auth_params_request``

**Direction:** Client → Server (UDP only)

**Format:**

.. code-block:: json

   {
     "type": "auth_params_request",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456"
   }

Parameters Response
^^^^^^^^^^^^^^^^^^^

Server provides authentication parameters (UDP only).

**Type:** ``auth_params``

**Direction:** Server → Client (UDP only)

**Format:**

.. code-block:: json

   {
     "type": "auth_params",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "salt": "abc123def456",
     "iterations": 100000
   }

**Fields:**

* ``salt`` (string): Salt for password hashing
* ``iterations`` (integer): PBKDF2 iteration count

Heartbeat Messages
~~~~~~~~~~~~~~~~~~

Heartbeat
^^^^^^^^^

Client sends periodic heartbeats to maintain connection.

**Type:** ``heartbeat``

**Direction:** Client → Server (TCP only)

**Format:**

.. code-block:: json

   {
     "type": "heartbeat",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456"
   }

Heartbeat Acknowledgment
^^^^^^^^^^^^^^^^^^^^^^^^^

Server acknowledges heartbeat.

**Type:** ``heartbeat_ack``

**Direction:** Server → Client (TCP only)

**Format:**

.. code-block:: json

   {
     "type": "heartbeat_ack",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456"
   }

Error Message
~~~~~~~~~~~~~

Reports errors to the peer.

**Type:** ``error``

**Direction:** Bidirectional

**Format:**

.. code-block:: json

   {
     "type": "error",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "error": "Error description",
     "code": 400
   }

**Fields:**

* ``error`` (string): Human-readable error description
* ``code`` (integer, optional): Error code

Connection Flows
----------------

TCP Connection Flow
~~~~~~~~~~~~~~~~~~~

1. **TCP Handshake**

   * Client initiates TCP connection to server
   * Three-way handshake (SYN, SYN-ACK, ACK)

2. **TLS Handshake** (if enabled)

   * Client and server negotiate TLS parameters
   * Server presents certificate
   * Encrypted channel established

3. **Authentication**

   .. code-block:: text

      Client                           Server
        │                                │
        │◄──── auth_challenge ───────────│
        │                                │
        │───── auth_response ───────────►│
        │                                │
        │◄──── auth_success ─────────────│
        │                                │

4. **Input Transmission**

   * Client sends ``input`` messages at configured rate
   * Client sends periodic ``heartbeat`` messages
   * Server acknowledges with ``heartbeat_ack``

5. **Disconnection**

   * Either side closes TCP connection
   * Clean shutdown with FIN packets

UDP Connection Flow
~~~~~~~~~~~~~~~~~~~

1. **Parameter Negotiation** (optional)

   .. code-block:: text

      Client                           Server
        │                                │
        │─── auth_params_request ───────►│
        │                                │
        │◄──── auth_params ──────────────│
        │                                │

2. **Input Transmission with Authentication**

   * Client computes authentication token for each message
   * Client sends ``input`` messages with ``token`` field
   * Server validates token and processes input
   * No connection state maintained

Authentication Details
----------------------

TCP Challenge-Response
~~~~~~~~~~~~~~~~~~~~~~

**Algorithm:**

1. Server generates 32-byte random challenge
2. Server sends challenge with password hash parameters (salt, iterations)
3. Client derives key from password using PBKDF2-HMAC-SHA256:

   .. code-block:: python

      key = PBKDF2(password, salt, iterations, dkLen=32)

4. Client computes HMAC-SHA256:

   .. code-block:: python

      response = HMAC-SHA256(key, challenge)

5. Client sends response to server
6. Server computes expected response and compares
7. Server grants or denies access

**Security Properties:**

* Challenge is single-use (prevents replay)
* Password never transmitted
* Resistant to brute-force (PBKDF2 iterations)

UDP Token Authentication
~~~~~~~~~~~~~~~~~~~~~~~~

**Algorithm:**

1. Client optionally requests auth parameters (salt, iterations)
2. Client derives key from password using PBKDF2
3. For each input message, client computes token:

   .. code-block:: python

      timestamp = current_time_seconds()
      message_data = json_without_token
      token = HMAC-SHA256(key, message_data + str(timestamp))

4. Client includes token in message
5. Server validates token using same computation
6. Server checks timestamp is recent (within 60 seconds)

**Security Properties:**

* Each message is authenticated
* Timestamp prevents replay attacks
* Password never transmitted
* Limited by 60-second window for clock skew

Rate Limiting
-------------

The server enforces rate limits to prevent abuse:

**Configuration:**

* ``rate_limit_window``: Time window in seconds (default: 60)
* ``max_requests``: Maximum requests per window (TCP: 100, UDP: 6000)
* ``block_duration``: Block time in seconds for violations (default: 2)

**Mechanism:**

1. Server tracks request count per client IP
2. When count exceeds ``max_requests`` in ``rate_limit_window``:
   * Client is blocked for ``block_duration`` seconds
   * Subsequent requests are rejected
3. After block expires, client can reconnect

**Response:**

* TCP: Connection closed with error message
* UDP: Messages silently dropped

Error Handling
--------------

Protocol Errors
~~~~~~~~~~~~~~~

**Invalid JSON:**

* TCP: Server sends ``error`` message and closes connection
* UDP: Message silently dropped

**Invalid Protocol Version:**

* TCP: Server sends ``error`` message with ``"protocol_mismatch"`` and closes connection
* UDP: Message silently dropped

**Missing Required Fields:**

* TCP: Server sends ``error`` message
* UDP: Message silently dropped

Connection Errors
~~~~~~~~~~~~~~~~~

**TCP:**

* Connection timeout: Client retries with exponential backoff
* Connection reset: Client attempts to reconnect
* TLS errors: Connection failed, client logs error

**UDP:**

* Packet loss: No retransmission, client continues sending
* Token validation failure: Server drops message, client continues

Compatibility
-------------

Version Negotiation
~~~~~~~~~~~~~~~~~~~

Currently, only version 1.0 is supported. Future versions may implement:

* Version negotiation during handshake
* Backward compatibility for older clients
* Feature flags for optional capabilities

Extensibility
~~~~~~~~~~~~~

The protocol is designed for future extensions:

* New message types can be added without breaking existing clients
* Unknown message types are logged and ignored
* Optional fields can be added to existing messages
* Clients check for fields before accessing

Constants
---------

.. code-block:: python

   PROTOCOL_VERSION = "1.0"
   DEFAULT_PORT = 9999
   HEARTBEAT_INTERVAL = 5.0  # seconds
   HEARTBEAT_TIMEOUT = 15.0  # seconds
   UDP_TOKEN_TTL = 60  # seconds
   DEFAULT_UPDATE_RATE = 60  # Hz

Message Size Limits
~~~~~~~~~~~~~~~~~~~

* Maximum message size: 65,507 bytes (UDP) / unlimited (TCP)
* Typical input message size: ~200 bytes
* Maximum buttons: Limited by JSON encoding
* Maximum axes: Limited by JSON encoding

Performance Considerations
--------------------------

Bandwidth Usage
~~~~~~~~~~~~~~~

**TCP:**

* Per input message: ~300 bytes (with TLS overhead)
* At 60 Hz: ~18 KB/s (~0.14 Mbps)
* Heartbeat: ~150 bytes every 5 seconds

**UDP:**

* Per input message: ~250 bytes
* At 60 Hz: ~15 KB/s (~0.12 Mbps)
* No heartbeat

Latency
~~~~~~~

* JSON parsing: <1ms
* HMAC computation: <1ms
* Network transmission: Varies (1-50ms typical)
* Total one-way latency: 3-55ms typical

See Also
--------

* :doc:`architecture` - System architecture
* :doc:`security` - Security design
* :doc:`api` - API reference
