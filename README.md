# PadRelay

Use a gamepad connected to one computer to play on another Windows PC.
PadRelay sends your button presses and stick movements over the network and
creates a virtual Xbox 360 or DualShock 4 controller on the receiving PC.

```text
Gamepad → Client computer → Network → Windows PC → Game
```

## What you need

- **Client:** a Windows, Linux or macOS computer with a gamepad supported by pygame.
- **Server:** the Windows PC running your game, with the ViGEmBus driver installed.
- **Both computers:** Python 3.11 or newer and compatible PadRelay versions.

Each server process supports one connected client and one virtual controller.

## Install

In an activated Python virtual environment, install PadRelay on the client:

```sh
python -m pip install padrelay
```

On the Windows server:

```sh
python -m pip install "padrelay[server]"
```

The server also needs the ViGEmBus driver. Follow the
[installation guide](docs/installation.rst) for driver and source installation.
These instructions describe the current repository; an older published package
may behave differently.

## Connect

This example connects two computers on the same local network using TCP with TLS.

### 1. Start the server

Create `server.ini` on the Windows PC. Replace the password with your own:

```ini
[server]
host = 0.0.0.0
port = 9999
protocol = tcp
password = replace-with-your-password

[vgamepad]
type = xbox360
```

Allow incoming TCP connections on port 9999 in Windows Firewall for your local
network, then run:

```sh
padrelay-server --config server.ini
```

The server creates `server.crt` and `server.key` in
`%USERPROFILE%\.padrelay\certs\`. Copy `server.crt` to the client through a
trusted channel. Keep `server.key` on the server.

### 2. Start the client

Connect your gamepad. Create `client.ini` with the Windows PC's local IP address,
the same password and the path to your certificate copy:

```ini
[network]
server_ip = 192.168.1.100
server_port = 9999
protocol = tcp
password = replace-with-your-password

[joystick]
index = 0

[security]
ca_path = /path/to/server.crt
server_hostname = localhost
```

Keep `server_hostname = localhost` when using the generated certificate: this
is the name on the certificate. The connection goes to `server_ip`.

```sh
padrelay-client --config client.ini
```

### 3. Check the controller

On the Windows PC, open `joy.cpl`, select the virtual controller and open its
properties. Press buttons and move the sticks to check that input arrives.
You can now use the virtual controller in your game. Stop either process with
`Ctrl+C`.

## More help

- [Controller mapping](docs/user_guide/key_mapper.rst) — fix button layouts or calibrate input.
- [Troubleshooting](docs/user_guide/troubleshooting.rst) — connection and controller problems.
- [Configuration](docs/configuration.rst) — settings and defaults.
- [Certificate setup](docs/user_guide/tls_setup.rst) — custom certificates and renewal.
- [UDP setup](docs/quickstart.rst#switch-to-udp-v2) — an alternative to TCP that needs both TCP and UDP ports open.
- [Upgrade notes](CHANGELOG.md) — changes and migration steps; update both computers when upgrading from older protocols.
- [Full documentation](https://ssh-den.github.io/PadRelay/) — all guides and technical references.

## Contributing

Bug reports, fixes, documentation and controller mappings are welcome.
Read the [contribution guide](docs/contributing.rst) and
[development guide](docs/development.rst) to get started.
Report security vulnerabilities privately to [sshden@duck.com](mailto:sshden@duck.com).

## License

PadRelay is available under the [MIT License](LICENSE).
