Architecture
============

This document provides an overview of PadRelay's internal architecture and design.

System Overview
---------------

PadRelay is a client-server application that transmits gamepad input across a network. The architecture is designed for:

* **Low latency:** Minimal processing between input capture and virtual gamepad output
* **Reliability:** Connection management, rate limiting, and error recovery
* **Security:** Authentication, optional TLS encryption, and input validation
* **Flexibility:** Support for TCP/UDP, multiple gamepad types, and custom mappings

Architecture Diagram
--------------------

::

    ┌─────────────────┐                           ┌──────────────────┐
    │  Physical       │                           │   Windows PC     │
    │  Gamepad        │                           │                  │
    └────────┬────────┘                           └────────┬─────────┘
             │                                              │
             │  USB / Bluetooth                             │  ViGEmBus
             │                                              │
             v                                              v
    ┌─────────────────┐                           ┌──────────────────┐
    │                 │                           │                  │
    │  PadRelay       │        Network            │  PadRelay        │
    │  Client         │◄─────────────────────────►│  Server          │
    │  (Any OS)       │   TCP/UDP + TLS           │  (Windows)       │
    │                 │                           │                  │
    └─────────────────┘                           └──────────────────┘
             │                                              │
             │                                              │
             v                                              v
    ┌─────────────────┐                           ┌──────────────────┐
    │  pygame         │                           │  vgamepad        │
    │  Input          │                           │  Virtual         │
    │  Capture        │                           │  Gamepad         │
    └─────────────────┘                           └──────────────────┘

Component Architecture
----------------------

Client Components
~~~~~~~~~~~~~~~~~

1. **Input Layer** (``padrelay.client.input``)

   * Captures gamepad input using pygame
   * Polls button states, axis positions, and D-pad directions
   * Normalizes input values to standard ranges

2. **Client Application** (``padrelay.client.client_app``)

   * Manages connection lifecycle
   * Handles authentication flow
   * Sends input messages at configured rate
   * Implements reconnection logic
   * Manages heartbeat

3. **Protocol Layer** (``padrelay.protocol``)

   * Message serialization/deserialization
   * Protocol version negotiation
   * Message validation

Server Components
~~~~~~~~~~~~~~~~~

1. **Server Application** (``padrelay.server.server_app``)

   * Accepts client connections
   * Manages authentication
   * Receives and processes input messages
   * Enforces rate limits
   * Manages virtual gamepad lifecycle

2. **Input Processor** (``padrelay.server.input_processor``)

   * Translates network messages to gamepad commands
   * Maps physical buttons to virtual buttons
   * Applies axis transformations (dead zones, inversion)
   * Handles trigger mappings

3. **Virtual Gamepad** (``padrelay.server.virtual_gamepad``)

   * Interfaces with vgamepad library
   * Creates Xbox 360 or DualShock 4 virtual controllers
   * Updates button and axis states
   * Manages gamepad lifecycle

Shared Components
~~~~~~~~~~~~~~~~~

1. **Protocol** (``padrelay.protocol``)

   * TCP handler (reliable, ordered delivery)
   * UDP handler (low latency, best effort)
   * Message types (input, heartbeat, auth, error)
   * Constants and protocol version

2. **Security** (``padrelay.security``)

   * Authentication (challenge/response, token-based)
   * Password hashing (PBKDF2)
   * TLS utilities (certificate generation, SSL context)
   * Rate limiting
   * Password strength validation
   * Log sanitization

3. **Configuration** (``padrelay.core.config``)

   * INI file parsing
   * Command-line argument handling
   * Configuration validation
   * Default value management

4. **Logging** (``padrelay.core.logging_utils``)

   * Centralized logging setup
   * Log rotation
   * Debug mode support
   * Sensitive data sanitization

Communication Flow
------------------

TCP Connection Flow
~~~~~~~~~~~~~~~~~~~

1. **Connection Establishment**

   .. code-block:: text

      Client                           Server
        │                                │
        │───── TCP Connect ─────────────►│
        │                                │
        │◄──── TLS Handshake ───────────►│ (if enabled)
        │                                │
        │◄──── Auth Challenge ───────────│
        │                                │
        │───── Auth Response ───────────►│
        │                                │
        │◄──── Auth Success ─────────────│
        │                                │

2. **Input Transmission**

   .. code-block:: text

      Client                           Server
        │                                │
        │───── Input Message ───────────►│ (at update_rate Hz)
        │                                │
        │───── Heartbeat ───────────────►│ (periodic)
        │◄──── Heartbeat Ack ────────────│
        │                                │

UDP Connection Flow
~~~~~~~~~~~~~~~~~~~

1. **Authentication**

   .. code-block:: text

      Client                           Server
        │                                │
        │───── Auth Params Request ─────►│ (if needed)
        │◄──── Auth Params ──────────────│
        │                                │
        │───── Input + Token ───────────►│ (HMAC-based token)
        │                                │

2. **Input Transmission**

   .. code-block:: text

      Client                           Server
        │                                │
        │───── Input + Token ───────────►│ (at update_rate Hz)
        │                                │

Message Format
--------------

All messages are JSON-encoded with the following base structure:

.. code-block:: json

   {
     "type": "message_type",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456"
   }

Input Message
~~~~~~~~~~~~~

.. code-block:: json

   {
     "type": "input",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "buttons": [0, 1, 4],
     "axes": [0.0, -0.5, 0.8, 0.0],
     "hats": [[0, 1]],
     "triggers": {
       "left": 0.0,
       "right": 0.7
     },
     "token": "hmac_value"  // UDP only
   }

Authentication Messages
~~~~~~~~~~~~~~~~~~~~~~~

**Challenge:**

.. code-block:: json

   {
     "type": "auth_challenge",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "challenge": "random_bytes_hex",
     "salt": "salt_hex",
     "iterations": 100000
   }

**Response:**

.. code-block:: json

   {
     "type": "auth_response",
     "protocol_version": "1.0",
     "timestamp": "2025-01-06T10:30:00.123456",
     "response": "hmac_hex"
   }

Security Architecture
---------------------

Authentication
~~~~~~~~~~~~~~

**TCP:** Challenge-response authentication

1. Server generates random challenge
2. Server sends challenge + hash parameters (salt, iterations)
3. Client computes HMAC using password-derived key
4. Server verifies HMAC
5. Connection established or rejected

**UDP:** Time-based token authentication

1. Each message includes HMAC token
2. Token computed from: message data + timestamp + password-derived key
3. Server verifies token and timestamp freshness
4. Prevents replay attacks (60-second window)

Password Hashing
~~~~~~~~~~~~~~~~

* **Algorithm:** PBKDF2-HMAC-SHA256
* **Iterations:** 100,000 (configurable)
* **Salt:** 16-byte random value
* **Storage format:** ``pbkdf2_sha256$iterations$salt$hash``

TLS/SSL
~~~~~~~

* **Minimum version:** TLS 1.2
* **Cipher suites:** Modern, secure ciphers (ECDHE, AES-GCM, ChaCha20)
* **Certificates:** Auto-generated self-signed or custom
* **TCP only:** UDP does not support TLS

Rate Limiting
~~~~~~~~~~~~~

* **Window-based:** Track requests per time window
* **Configurable:** Different limits for TCP (100/min) and UDP (6000/min)
* **Blocking:** Temporarily block abusive clients
* **Per-client:** Rate limits applied per client address

Data Flow
---------

Input Capture to Virtual Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Capture** (Client)

   * pygame polls physical gamepad
   * Read button states (pressed/released)
   * Read axis positions (-1.0 to 1.0)
   * Read D-pad directions

2. **Serialize** (Client)

   * Create InputMessage with current state
   * Add authentication token (UDP)
   * Encode to JSON
   * Send over network

3. **Receive** (Server)

   * Accept TCP connection or UDP datagram
   * TLS decrypt (TCP only)
   * Parse JSON message
   * Validate protocol version and structure

4. **Authenticate** (Server)

   * Verify HMAC token (UDP) or challenge-response (TCP)
   * Check rate limits
   * Reject if invalid

5. **Process** (Server)

   * Map physical button IDs to virtual button constants
   * Apply axis transformations (dead zone, inversion)
   * Normalize trigger values

6. **Output** (Server)

   * Update vgamepad virtual controller
   * Press/release virtual buttons
   * Set virtual stick positions
   * Set virtual trigger values
   * Windows sees virtual gamepad input

Threading Model
---------------

Client
~~~~~~

* **Main thread:** Event loop for connection management
* **Async tasks:** Input polling, message sending, heartbeat

Server
~~~~~~

* **TCP:** One async task per client connection
* **UDP:** Single async task for all clients
* **Main thread:** Server lifecycle management

Configuration System
--------------------

The configuration system supports multiple sources with clear priority:

1. **Environment variables:** Highest priority (passwords, log directory, debug mode)
2. **Command-line arguments:** Override config file settings
3. **Configuration files:** INI format with sections
4. **Defaults:** Built-in fallback values

Example flow:

.. code-block:: python

   # 1. Load config file
   config = load_config("server_config.ini")

   # 2. Parse command-line args
   args = parse_args()

   # 3. Apply precedence
   password = os.getenv("PASSWORD") or args.password or config["password"]

   # 4. Validate
   validate_config(final_config)

Extension Points
----------------

Custom Button Mappings
~~~~~~~~~~~~~~~~~~~~~~

Users can define custom mappings in configuration:

.. code-block:: ini

   [button_mapping_xbox360]
   0 = XUSB_GAMEPAD_B     # Swap A and B
   1 = XUSB_GAMEPAD_A
   2 = XUSB_GAMEPAD_X
   3 = XUSB_GAMEPAD_Y

Custom Axis Transformations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Axis options support various transformations:

* Dead zones (ignore small movements)
* Inversion (reverse axis direction)
* Thresholds (trigger sensitivity)

Future extensibility could add:

* Custom scaling functions
* Axis remapping
* Macro support

Performance Considerations
--------------------------

Latency Sources
~~~~~~~~~~~~~~~

1. **Input polling:** ~1ms (60-120 Hz)
2. **Serialization:** <1ms (JSON encoding)
3. **Network transmission:** 1-50ms (depends on network)
4. **Deserialization:** <1ms (JSON decoding)
5. **vgamepad update:** ~1ms

**Total typical latency:** 5-55ms

Optimization Strategies
~~~~~~~~~~~~~~~~~~~~~~~

1. **Use UDP:** Eliminates TCP handshake and retransmission delays
2. **Increase update rate:** Higher Hz = lower perceived latency
3. **Reduce network hops:** Same LAN = lower latency
4. **Minimize processing:** Efficient serialization, minimal transformations
5. **Async I/O:** Non-blocking operations prevent backlog

Memory Usage
~~~~~~~~~~~~

* **Client:** ~10-20 MB (pygame + Python runtime)
* **Server:** ~15-30 MB (vgamepad + Python runtime)
* **Per connection:** ~1-2 MB (buffers, state)

Design Principles
-----------------

1. **Simplicity:** Easy to install, configure, and use
2. **Security:** Authentication, encryption, input validation
3. **Reliability:** Error handling, reconnection, rate limiting
4. **Performance:** Low latency, efficient serialization
5. **Flexibility:** Multiple protocols, gamepad types, custom mappings
6. **Portability:** Cross-platform client, standard Python
7. **Maintainability:** Clear separation of concerns, documented code

See Also
--------

* :doc:`protocol` - Detailed protocol specification
* :doc:`security` - Security design and best practices
* :doc:`api` - API reference documentation
