# PadRelay

**PadRelay** forwards gamepad input from a local machine to a Windows PC where a virtual controller is created using the `vgamepad` library.  The client captures input with `pygame` and the server emulates either an Xbox 360 or DualShock 4 gamepad.

## Features

- Works with Python 3.6+ on any system with `pygame` for the client
- Windows server with [ViGEmBus](https://github.com/ViGEm/ViGEmBus) installs a virtual gamepad
- Supports TCP (reliable) or UDP (low latency) transport
- Challenge/response authentication for TCP and token authentication for UDP
- Heartbeat and rate limiting to keep connections healthy
- Configurable block duration and higher defaults for UDP to avoid false limits
- Automatic reconnection if the server disconnects

## Installation

Clone the repository and install the Python requirements if you want to run the
scripts directly from source:

```bash
pip install -r requirements.txt
```

After installing the dependencies, you can run the applications directly from source with: `python scripts/server.py` and
`python scripts/client.py`.

Alternatively install the package in editable mode to make the console commands
available:

```bash
pip install -e .
```

This will expose `padrelay-server` and `padrelay-client` on your `PATH`. When the
project will be published on PyPI you may also install it with `pip install
padrelay`.

When running the server on Windows install `vgamepad` and
[ViGEmBus](https://github.com/ViGEm/ViGEmBus) as well.

## Configuration

Example INI files live in the `config/` directory.  A trimmed server configuration looks like:
For a detailed explanation of every setting see [the full configuration reference](CONFIGURATION.md).

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

## Disclaimer

**Security Notice**

PadRelay does **not** implement TLS or any built-in encryption. It is intended for use on **trusted, private networks** only.  
You should always secure communication via a **VPN, SSH tunnel**, or other private channel. **Never expose the server directly to the public internet.**

Use this software **at your own risk**. The author assumes no responsibility for data loss, damage, or security issues resulting from its use.

**Bug Reports**

This project is under active development. If you encounter any issues, misbehavior, or unexpected crashes, please open an issue on GitHub with steps to reproduce.  
Contributions and pull requests are always welcome.
