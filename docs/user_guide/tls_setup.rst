TLS and Certificate Trust
=========================

TCP enables TLS by default in the CLI. UDP v2 requires verified TLS control and
uses the same certificate settings; allow both TCP and UDP on the server port.
Certificate or TLS setup failures do not trigger a plaintext fallback.

Default Self-Signed Identity
----------------------------

Start the server with a password and no custom certificate paths. It generates
``server.crt`` and ``server.key`` in ``~/.padrelay/certs/``
(``%USERPROFILE%\.padrelay\certs\`` on Windows) if both files are absent.
The default certificate uses RSA-2048, lasts 365 days, and identifies
``localhost`` and ``127.0.0.1`` through Subject Alternative Names.

Copy **only the public certificate** to the client through a trusted channel.
Never copy ``server.key``. Trust the local copy and use the identity in it:

.. code-block:: bash

   padrelay-client --config client.ini --server-ip 192.168.1.100 \
     --ca-path /path/to/trusted-server.crt --server-hostname localhost

Here the destination is the LAN IP, while the certificate is checked against
``localhost``. ``--server-hostname`` changes the expected identity, not the
connection address or verification policy. A separate CA is not needed for
an explicitly trusted self-signed certificate.

The equivalent client settings are:

.. code-block:: ini

   [security]
   ca_path = /path/to/trusted-server.crt
   server_hostname = localhost

Omit ``ca_path`` to use system trust. A private CA normally needs its CA bundle
there instead. An untrusted chain, expired certificate, incorrect hostname or
missing trust file fails the connection. Correct the trust setup rather than
disabling verification.

Custom Identity
---------------

Supply both server paths:

.. code-block:: ini

   [security]
   cert_path = /path/to/server-chain.pem
   key_path = /path/to/server.key

Or use ``--cert-path`` and ``--key-path``. Both files must exist, load correctly
and match. The certificate file should include any required intermediates.
The client still needs a matching trust root and expected SAN name/IP.

To create a custom self-signed identity with the project's generator, choose
new output paths:

.. code-block:: python

   from pathlib import Path
   from padrelay.security.tls_utils import generate_self_signed_cert

   generate_self_signed_cert(
       cert_path=Path("new-server.crt"),
       key_path=Path("new-server.key"),
       common_name="padrelay.local",
   )

The generator adds the supplied name/IP to the default localhost SANs. Existing
files and symlinks are not overwritten. Copy the public certificate to clients
and use ``server_hostname = padrelay.local`` if connecting by another address.

Inspect and Renew
-----------------

If OpenSSL is available, inspect the certificate and compare its fingerprint
over a trusted channel:

.. code-block:: bash

   openssl x509 -in server.crt -noout -dates -fingerprint -sha256

The server warns within 30 days of expiry. It does not renew automatically.
Stop the server, replace the matching certificate/key pair, and restart it.
For the default generator, move both old identity files out of the default
paths before restarting; leaving just one causes startup to fail.

When replacing a self-signed identity, distribute the new public certificate
and update every client's trust copy. A CA-issued leaf renewed under the same
trusted CA does not normally require a new client trust bundle.

Generated files use POSIX mode ``0600`` and the default directory ``0700``.
For Windows and custom directories, restrict access through the appropriate
ACLs or filesystem permissions. Do not place private keys in shared configs.

Diagnose Trust Failures
-----------------------

With OpenSSL, test just the TLS layer for either transport mode:

.. code-block:: bash

   openssl s_client -connect 192.168.1.100:9999 \
     -CAfile trusted-server.crt -verify_hostname localhost -verify_return_error

Use your actual certificate name. This does not authenticate as a PadRelay
client or test UDP input. For application failures, see :doc:`troubleshooting`.

``--disable-tls`` works only for TCP and must match on both peers. UDP rejects
it, even inside a VPN. There is no CLI option to keep TLS but ignore certificate
verification; the low-level SSL helper's insecure opt-out is not used by the CLI.
