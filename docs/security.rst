Security
========

The CLI requires a password for both transports. TCP enables verified TLS by
default; UDP v2 requires it for control and uses AES-256-GCM for input. There is
no automatic fallback to plaintext after a trust or TLS setup failure.

Trust and Credentials
---------------------

The client checks the server's certificate chain, validity and expected name.
Use the system trust store, a private CA bundle, or a trusted copy of the
self-signed server certificate. Certificate distribution and renewal are
covered in :doc:`user_guide/tls_setup`.

Password authentication uses a fresh challenge and HMAC-SHA256 over a
PBKDF2-derived key. A stored hash is a usable login credential, not safe public
data: anyone with its digest can compute valid responses. Protect it like the
password. A client hash must match the server's exact hash, including its salt;
independently hashing the same password does not produce a matching credential.

PBKDF2-HMAC-SHA256 uses 100000 iterations by default, a random salt encoded as
32 hex characters, and a 32-byte digest. All hashing entry points reject work
factors outside 100000–600000 or non-ASCII salts outside 16–128 characters.
The client validates network parameters before dispatching derivation to a
worker thread. Authentication state changes only after the worker completes;
cancellation cannot commit an unfinished derivation.

The server may rewrite a plaintext ``[server] password`` in its INI file to
``pbkdf2_sha256$iterations$salt$digest``. This does not apply to the client config
or passwords supplied through environment variables. See :doc:`configuration`
for credential precedence and migration behavior.

Transport Protection
--------------------

TCP/TLS protects input and control messages. Both SSL contexts require TLS 1.2
or newer. UDP session IDs and keys are issued only after password authentication
inside the TLS control connection. Each key has one sender, a sequence counter
that never wraps, and a maximum lifetime of 600 seconds.

UDP authenticates the entire header and payload before committing replay state.
A 64-packet bitmap rejects duplicates; stale reordered input does not overwrite
newer gamepad state. Sessions are bound to the control peer IP and are removed
when control closes. See :doc:`protocol` for encodings and size limits.

``--disable-tls`` is available only for TCP and must be applied consistently to
both peers. It removes encryption and server identity verification, including
protection of the password challenge exchange. It is not a remedy for certificate
errors. UDP rejects the flag and ``[security] enable_tls = false``.

Admission and Resource Limits
-----------------------------

The server reserves a slot synchronously before waiting for authentication.
Pending and authenticated clients share a default limit of one. The slot is
separate from limiter records and is released by its owning handler, including
on timeout, cancellation and shutdown. Rejected clients do not reset another
client's gamepad.

TLS handshake and application authentication each have a five-second deadline.
Closing an admitted connection waits at most one second before aborting its
transport. These application slots are reserved after TLS completes; they do
not cap all sockets or memory allocated during the TLS handshake itself.

Two independent token-bucket limiters use monotonic time:

.. list-table::
   :header-rows: 1

   * - Traffic
     - Per-IP capacity
     - Global capacity
     - Refill period
   * - UDP datagrams
     - ``max_requests`` (CLI default 6000)
     - 12000
     - ``rate_limit_window`` (default 60 seconds)
   * - Authentication attempts
     - ``min(max_requests, 10)``
     - 1000
     - 60 seconds

Buckets allow an initial burst up to capacity, then refill continuously.
All ports from one IP share its bucket, including peers behind a NAT. UDP is
limited before parsing or decryption. TCP's ``max_requests`` does not limit
authenticated input updates; it affects the authentication budget above.

Each limiter stores at most 1024 IP records with constant-sized state. At
capacity, new IPs are rejected without evicting existing blocks. Idle records
expire; cleanup runs at most once a second. Exhausting a bucket causes a
temporary block: UDP uses ``block_duration`` (default two seconds), while the
authentication limiter uses its fixed two-second default. Global buckets also
block temporarily on exhaustion. These ceilings are implementation defaults,
not additional CLI options.

Input and Local Files
---------------------

Every input is validated before gamepad processing. Buttons must be booleans,
axes within [-1, 1], triggers within [0, 1], and hats integer pairs in {-1, 0, 1}.
Invalid messages are discarded. Neither transport accepts payloads beyond its
4096-byte receive limit.

Generated certificate files are created exclusively with POSIX mode ``0600``;
the default certificate directory uses ``0700``. Existing identities are not
overwritten. Use appropriate Windows ACLs and restrict access to custom identity
directories, configuration and logs. INI loading warns about group/world-readable
files; it does not correct their permissions.

Logging does not provide universal secret redaction. The sanitization helper
escapes newlines, removes other control characters and truncates text, but
callers must use it explicitly. Review diagnostic output before sharing it.

Scope
-----

Encryption does not protect compromised endpoints, hide traffic timing, or stop
network saturation. Use firewall or VPN access controls to restrict who can
reach the listener; application rate limits do not replace those boundaries.
Password-strength checks warn rather than reject weak passwords.

Report vulnerabilities privately using :doc:`contributing`, without publishing
credentials or private keys.
