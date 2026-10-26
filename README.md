# PadRelay

Forward physical gamepad input to a virtual Xbox 360 or DualShock 4 controller
on a Windows PC. The client reads input with pygame; the server uses vgamepad
and ViGEmBus. Requires **Python 3.11+**.

| Mode | Input | Control and login | Firewall |
| --- | --- | --- | --- |
| TCP (default) | Ordered JSON stream over TLS | Same TLS stream | TCP port |
| UDP v2 | AES-256-GCM datagrams with replay checks | Verified TLS on the same port number | TCP and UDP port |

One server process owns one virtual gamepad and admits one pending or
authenticated client. UDP still requires a password and server certificate
trust; legacy bearer tokens and unauthenticated UDP are rejected.
See the [2.0.0 migration notes](CHANGELOG.md#200---2026-10-26) before upgrading older peers.

## Install

In an activated Python environment:

```sh
python -m pip install padrelay
```

On the Windows server, install the server extra and the ViGEmBus driver:

```sh
python -m pip install "padrelay[server]"
```

See the [installation guide](https://ssh-den.github.io/PadRelay/installation.html)
for source installs, drivers and environment checks. Current repository behavior
may differ from an older published package; use compatible builds on both peers.

## First Connection

1. Follow the [quick start](https://ssh-den.github.io/PadRelay/quickstart.html)
   with separate server and client INI files. For remote clients, bind the server
   to its LAN address or `0.0.0.0`; the built-in default is local-only.
2. Start the server. Copy its public `server.crt` to the client through a trusted
   channel; keep `server.key` on the server.
3. Set the client's `ca_path` to that trusted copy. With the generated localhost
   certificate reached through a LAN IP, set `server_hostname = localhost`.
4. Run `padrelay-client --config client.ini` and check the virtual device in
   Windows `joy.cpl`.

The server's default identity lives in `~/.padrelay/certs/`. Both peers use the
same password, or the client uses the server's exact encoded hash. Credential
precedence and INI migration are in the [configuration reference](docs/configuration.rst).

For UDP, change both peers to `protocol = udp`, allow both port protocols and
set a suitable server packet budget, normally `max_requests = 6000` at 60 Hz.
An explicit TCP value of 100 in a copied INI is not replaced automatically.
Sessions reconnect after ten minutes with a new key. TLS cannot be disabled
for UDP, even over a VPN.

## Documentation

- [Client and server setup](https://ssh-den.github.io/PadRelay/quickstart.html)
- [Certificate trust and renewal](docs/user_guide/tls_setup.rst)
- [Controller mapping](docs/user_guide/key_mapper.rst)
- [Troubleshooting](docs/user_guide/troubleshooting.rst)
- [Security boundaries](docs/security.rst) and [wire protocol](docs/protocol.rst)
- [Development](docs/development.rst) and [contributing](docs/contributing.rst)

To configure a controller, run `padrelay-keymapper --output controller.ini` and
merge its mapping sections into the **server** configuration. Hat-only D-pads
are not currently applied to virtual output; see the mapping guide for limits.

Logs default to `~/.padrelay/logs/padrelay.log`. Set `PADRELAY_DEBUG=1` for
diagnostics or `PADRELAY_LOG_DIR` to change the directory. The CLI has no
`--version` flag; use `python -m pip show padrelay`.

## Development

From an activated `.venv` in a checkout:

```sh
python -m pip install -e ".[dev]"
```

The [development guide](docs/development.rst) lists the checks and documentation
build commands. CI checks Python 3.11 and 3.12 on pushes and pull requests.
Documentation and package publishing remain separate manual workflows.

PadRelay is licensed under the [MIT License](LICENSE). Report vulnerabilities
privately through the [contribution guide](docs/contributing.rst).
