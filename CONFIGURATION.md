# Configuration

This document describes every configuration option and command line flag
available in **PadRelay**. The configuration files use the
standard INI format. Example files live in the `config/` directory.

Values provided on the command line override those in configuration files.
Environment variables have the highest priority.

## Client Settings

### `[network]`
- `server_ip` – IP address of the gamepad server. Defaults to `127.0.0.1`.
- `server_port` – Port number the server listens on. Defaults to `9999`.
- `protocol` – `tcp` for reliable connections or `udp` for low latency. Defaults to `tcp`.
- `password` – Plaintext password for TCP authentication. Optional for UDP.
- `password_hash` – Pre-hashed password used by UDP clients so the secret is never stored in plaintext.

### `[joystick]`
- `index` – Index of the local gamepad to use. Defaults to `0`.

### `[client]`
- `update_rate` – How often input is sent to the server in Hertz. Defaults to `60`.

### Client Command Line Flags
- `--server-ip` – Same as `server_ip`.
- `--server-port` – Same as `server_port`.
- `--protocol` – Same as `protocol`.
- `--joystick-index` – Same as `index`.
- `--update-rate` – Same as `update_rate`.
- `--password` – Provide the plaintext password on the command line.
- `--password-hash` – Provide a pre-hashed password (overrides `--password`).
- `--config` – Path to a configuration file to load settings from.

## Server Settings

### `[server]`
- `host` – Interface to bind to. Defaults to `127.0.0.1`.
- `port` – Port to listen on. Defaults to `9999`.
- `protocol` – `tcp` or `udp`. Defaults to `tcp`.
- `password` – Authentication password. Stored as a PBKDF2 hash on first run.
- `rate_limit_window` – Time window in seconds for rate limiting. Defaults to `60`.
- `max_requests` – Maximum requests per window. Defaults to `100` for TCP and `6000` for UDP.
- `block_duration` – Seconds to block clients that exceed the rate limit. Defaults to `2`.

### `[vgamepad]`
- `type` – Virtual controller type: `xbox360` or `ds4`. Defaults to `xbox360`.

### `[button_mapping_xbox360]` / `[button_mapping_ds4]`
Mapping sections that translate physical button numbers to virtual button
constants from the `vgamepad` library.

### `[axis_mapping]`
Maps axis names (`left_stick_x`, `left_stick_y`, `right_stick_x`,
`right_stick_y`, `trigger_left`, `trigger_right`) to physical axis indexes.

### `[axis_options]`
- `dead_zone` – Value below which stick movement is ignored.
- `trigger_threshold` – Minimum trigger value reported as pressed.
- `invert_left_y` – `true` to invert the Y axis of the left stick.
- `invert_right_y` – `true` to invert the Y axis of the right stick.

### Server Command Line Flags
- `--host` – Same as `host`.
- `--port` – Same as `port`.
- `--protocol` – Same as `protocol`.
- `--password` – Provide authentication password.
- `--gamepad-type` – Same as `[vgamepad] type`.
- `--rate-limit-window` – Same as `rate_limit_window`.
- `--max-requests` – Same as `max_requests`.
- `--block-duration` – Same as `block_duration`.
- `--config` – Path to a configuration file.

## Environment Variables
- `PASSWORD` – Overrides any configured plaintext password.
- `PASSWORD_HASH` – Overrides any configured password with a pre-hashed value.
- `PADRELAY_LOG_DIR` – Directory where log files are written.

## Notes
- When the server reads a configuration containing a plaintext `password`
  it automatically replaces it with a PBKDF2 hash.
- UDP mode does not use TLS. Consider running **PadRelay** only on a trusted
  local network or within a VPN.
