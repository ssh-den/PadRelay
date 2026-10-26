# PadRelay

**PadRelay** forwards gamepad input from a local machine to a Windows PC where a virtual controller is created using the `vgamepad` library.  The client captures input with `pygame` and the server emulates either an Xbox 360 or DualShock 4 gamepad.

## Features

- Works with Python 3.6+ on any system (Linux, MacOS, Windows) with `pygame` for the client
- Windows server with [ViGEmBus](https://github.com/ViGEm/ViGEmBus) installs a virtual gamepad
- Supports TCP (reliable) or UDP (low latency) transport
- Challenge/response authentication for TCP and token authentication for UDP
- Heartbeat and rate limiting to keep connections healthy
- Configurable block duration and higher defaults for UDP to avoid false limits
- Automatic reconnection if the server disconnects

## Installation

You can install PadRelay directly from [PyPI](https://pypi.org/project/padrelay/):

```bash
pip install padrelay
```

This will install the padrelay-server and padrelay-client command-line tools globally in your PATH. It also provides a `padrelay-keymapper` utility for creating controller mappings.

To run the server and client:

```bash
padrelay-server --config config/server_config.ini
padrelay-client --config config/client_config.ini
padrelay-keymapper --output my_config.ini
```

See the [full documentation](https://padrelay.readthedocs.io) for detailed guides.

#### From Source (Development Mode)

If you want to run the project directly from source (e.g. for development), clone the repository and install dependencies:

```bash
git clone https://github.com/ssh-den/PadRelay.git
cd PadRelay
pip install -r requirements.txt
```

Then either run the scripts directly:

```bash
python scripts/server.py --config config/server_config.ini
python scripts/client.py --config config/client_config.ini
```

Or install in editable mode to expose the CLI tools:

```bash
pip install -e .
```

When running the server on Windows install [vgamepad](https://pypi.org/project/vgamepad/) and
[ViGEmBus](https://github.com/ViGEm/ViGEmBus) as well.

## Configuration

Example INI files live in the `config/` directory.  A trimmed server configuration looks like:
For a detailed explanation of every setting see the [configuration documentation](https://padrelay.readthedocs.io/en/latest/configuration.html).

```ini
[server]
host = 127.0.0.1
port = 9999
protocol = tcp
password = your_secure_password
rate_limit_window = 60
max_requests = 100
block_duration = 2
```

On first run the server will replace any plaintext `password` value with a
PBKDF2 hash string so the file no longer contains the original secret.  Use the
`PASSWORD` or `PASSWORD_HASH` environment variable to override the value without
modifying the configuration file. When the password is stored as a hash the
server automatically includes the hash parameters in its authentication
challenge so clients using the original plaintext password continue to work.

```ini
[vgamepad]
type = xbox360
```

and a matching client configuration:

```ini
[network]
server_ip = 192.168.1.100
server_port = 9999
protocol = tcp
password = your_secure_password

[joystick]
index = 0

[client]
update_rate = 60
```

## Usage

If you installed the project with `pip install -e .` or from PyPI you can use
the `padrelay-server` and `padrelay-client` commands. When running directly from
source replace them with `python scripts/server.py` and
`python scripts/client.py`.

Start the server with your configuration:

```bash
padrelay-server --config config/server_config.ini
```

Then start the client and point it at the server:

```bash
padrelay-client --config config/client_config.ini
```

Both scripts accept command line flags (see `--help`) and load values from the configuration files if provided.
The server also checks the `PASSWORD` or `PASSWORD_HASH` environment variables
which override any configured value at runtime. Clients may specify a
`--password-hash` argument, a `[network] password_hash` setting, or the
`PASSWORD_HASH` environment variable when using UDP so the secret never needs to
be stored in plaintext.

When a client only has the plaintext password for UDP, it will automatically
send an `auth_params_request` when connecting. Servers that store only a hashed
password reply with their salt and iteration count so the client can derive the
same key and authenticate using time‑based tokens. Servers using a plaintext
password simply ignore the request and the client continues with the plaintext
key.

## Testing

To run the unit tests:

```bash
pytest
```

## Logging

All components write logs to a single file in the `logs` directory at the project
root by default. The directory will be created automatically if it does not
exist. Set the ``PADRELAY_LOG_DIR`` environment variable to override this
location. Logs are rotated automatically and never include passwords or tokens.

## Documentation

📚 **Comprehensive documentation is available at [https://padrelay.readthedocs.io](https://padrelay.readthedocs.io)**

* [Installation Guide](https://padrelay.readthedocs.io/en/latest/installation.html)
* [Quick Start](https://padrelay.readthedocs.io/en/latest/quickstart.html)
* [Configuration Reference](https://padrelay.readthedocs.io/en/latest/configuration.html)
* [TLS/SSL Setup](https://padrelay.readthedocs.io/en/latest/user_guide/tls_setup.html)
* [Troubleshooting](https://padrelay.readthedocs.io/en/latest/user_guide/troubleshooting.html)
* [API Reference](https://padrelay.readthedocs.io/en/latest/api.html)

## Security

**Version 1.1.0+ includes TLS/SSL support!**

* TLS encryption is **enabled by default** for TCP connections
* Automatic self-signed certificate generation
* PBKDF2 password hashing for secure authentication
* Rate limiting to prevent abuse

For best security:
* Use TLS for all TCP connections (enabled by default)
* Use strong passwords (12+ characters)
* Run on trusted private networks or VPNs
* Never expose the server directly to the public internet

See the [Security Documentation](https://padrelay.readthedocs.io/en/latest/security.html) for details.

Use this software **at your own risk**. The author assumes no responsibility for data loss, damage, or security issues resulting from its use.

## Contributing

Contributions are welcome! Please see the [Contributing Guide](https://padrelay.readthedocs.io/en/latest/contributing.html) for details.

**Bug Reports:** Open an issue on GitHub with steps to reproduce.

**Feature Requests:** Suggest improvements via GitHub issues.

**Pull Requests:** Fork the repository, make changes, and submit a PR.

## Links

* **Documentation:** https://padrelay.readthedocs.io
* **PyPI:** https://pypi.org/project/padrelay/
* **GitHub:** https://github.com/ssh-den/PadRelay
* **Issues:** https://github.com/ssh-den/PadRelay/issues

## License

MIT License - see [LICENSE](LICENSE) file for details.
