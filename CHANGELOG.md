# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [1.1.0] - 2025-11-06

### Added
- **TLS/SSL Support**: Optional TLS/SSL encryption for TCP connections with automatic self-signed certificate generation
  - `--enable-tls` / `--disable-tls` flags for both client and server
  - Automatic certificate generation and management (stored in `~/.padrelay/certs/`)
  - Certificate expiration warnings
  - TLS 1.2+ minimum version requirement
  - Server: `--cert-path` and `--key-path` options for custom certificates
- **Password Strength Warnings**: Non-enforcing password strength checking with recommendations
  - Automatic password strength analysis on startup
  - Detailed recommendations for improving weak passwords
  - Warnings about very weak or commonly used passwords
- **Security Enhancements**:
  - Log sanitization to prevent log injection attacks
  - Config file permission warnings for world-readable files
- **Dependencies**: Added `cryptography>=41.0.0` and `cffi>=1.15.0` for TLS support

### Changed
- TLS/SSL is now enabled by default for TCP connections (can be disabled with `--disable-tls`)
- Enhanced security warnings throughout the application
- Improved error messages for security-related issues

## [1.0.4] - 2025-06-15

### Added
- `padrelay-keymapper` CLI for creating controller mapping files

## [1.0.3] - 2025-06-14

### Fixed
- Synced GitHub release and PyPI version numbers to avoid mismatch
- Ensured correct artifacts attached to GitHub Releases

## [1.0.2] - 2025-06-14

### Fixed
- Corrected `version` field in `pyproject.toml` to match intended release

## [1.0.1] - 2025-06-14

### Added
- CI: GitHub Actions workflow for testing with pytest (`python-tests.yml`)
- CI: GitHub Actions workflow for building and publishing releases on tag push (`release.yml`)

## [1.0.0] - 2025-06-14

- initial release

<!-- Links -->
[keep a changelog]: https://keepachangelog.com/en/1.0.0/
[semantic versioning]: https://semver.org/spec/v2.0.0.html

<!-- Versions -->
[1.1.0]: https://github.com/ssh-den/PadRelay/releases/tag/v1.1.0
[1.0.4]: https://github.com/ssh-den/PadRelay/releases/tag/v1.0.4
[1.0.3]: https://github.com/ssh-den/PadRelay/releases/tag/v1.0.3
[1.0.2]: https://github.com/ssh-den/PadRelay/releases/tag/v1.0.2
[1.0.1]: https://github.com/ssh-den/PadRelay/releases/tag/v1.0.1
[1.0.0]: https://github.com/ssh-den/PadRelay/releases/tag/v1.0.0
