"""Helpers for reading and validating configuration"""
import argparse
import configparser
import getpass
import os
from ..security.auth import Authenticator
from ..security.password_strength import warn_weak_password
from typing import Optional, Tuple
from .logging_utils import get_logger
from ..server.constants import (
    DEFAULT_MAX_REQUESTS,
    DEFAULT_RATE_LIMIT_WINDOW,
    DEFAULT_UDP_MAX_REQUESTS,
    DEFAULT_BLOCK_DURATION,
)

logger = get_logger(__name__)

def load_config(config_path: str) -> Optional[configparser.ConfigParser]:

    config = configparser.ConfigParser()
    try:
        # Check file permissions (warn if world-readable)
        import stat
        from pathlib import Path
        config_file = Path(config_path)
        if config_file.exists():
            file_stat = config_file.stat()
            mode = file_stat.st_mode
            # Check if file is world-readable (others can read)
            if mode & stat.S_IROTH:
                logger.warning(
                    f"Configuration file {config_path} is world-readable! "
                    "This is a security risk if the file contains passwords. "
                    f"Consider setting permissions to 600: chmod 600 {config_path}"
                )
            # Check if file is group-readable
            elif mode & stat.S_IRGRP:
                logger.warning(
                    f"Configuration file {config_path} is group-readable. "
                    f"Consider setting permissions to 600 for better security: chmod 600 {config_path}"
                )

        with open(config_path, 'r') as f:
            config.read_file(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return None

def parse_client_args() -> Tuple[argparse.Namespace, Optional[configparser.ConfigParser]]:

    parser = argparse.ArgumentParser(description="PadRelay Client")
    parser.add_argument("--server-ip", type=str, help="IP address of the server")
    parser.add_argument("--server-port", type=int, help="Server port")
    parser.add_argument("--protocol", type=str, choices=["tcp", "udp"], help="Transport protocol (tcp or udp)")
    parser.add_argument("--joystick-index", type=int, help="Index of the joystick to use")
    parser.add_argument("--update-rate", type=int, help="Update rate in Hz")
    parser.add_argument("--config", type=str, help="Path to configuration file (INI format)")
    parser.add_argument("--password", type=str, help="Authentication password")
    parser.add_argument(
        "--password-hash",
        type=str,
        help="Pre-hashed authentication password (overrides --password)",
    )
    parser.add_argument(
        "--enable-tls",
        action="store_true",
        help="Enable TLS/SSL encryption (recommended for security)",
    )
    parser.add_argument(
        "--disable-tls",
        action="store_true",
        help="Disable TLS/SSL encryption (use only on trusted networks)",
    )
    args = parser.parse_args()

    env_password = os.getenv("PASSWORD")
    env_hash = os.getenv("PASSWORD_HASH")

    config_obj = None
    if args.config:
        config_obj = load_config(args.config)
        if config_obj and config_obj.has_section('network'):
            if not args.server_ip and 'server_ip' in config_obj['network']:
                args.server_ip = config_obj['network']['server_ip']
            if not args.server_port and 'server_port' in config_obj['network']:
                args.server_port = config_obj.getint('network', 'server_port')
            if not args.protocol and 'protocol' in config_obj['network']:
                args.protocol = config_obj['network']['protocol']
            if (
                not args.password
                and not args.password_hash
                and 'password' in config_obj['network']
            ):
                args.password = config_obj['network']['password']
            if not args.password_hash and 'password_hash' in config_obj['network']:
                args.password_hash = config_obj['network']['password_hash']
        if config_obj and config_obj.has_section('joystick'):
            if not args.joystick_index and 'index' in config_obj['joystick']:
                args.joystick_index = config_obj.getint('joystick', 'index')
        if config_obj and config_obj.has_section('client'):
            if not args.update_rate and 'update_rate' in config_obj['client']:
                args.update_rate = config_obj.getint('client', 'update_rate')

        # TLS settings
        if config_obj and config_obj.has_section('security'):
            if 'enable_tls' in config_obj['security'] and not args.enable_tls and not args.disable_tls:
                tls_enabled = config_obj.getboolean('security', 'enable_tls')
                if tls_enabled:
                    args.enable_tls = True
                else:
                    args.disable_tls = True

    # Set defaults if not provided
    if not args.server_ip:
        args.server_ip = "127.0.0.1"
    if not args.server_port:
        args.server_port = 9999
    if not args.protocol:
        args.protocol = "tcp"
    if not args.joystick_index:
        args.joystick_index = 0
    if not args.update_rate:
        args.update_rate = 60

    # Apply environment overrides
    if env_password:
        args.password = env_password
    if env_hash:
        args.password_hash = env_hash

    # Finalize password selection
    if args.password_hash:
        args.password = args.password_hash
    elif not args.password and args.protocol.lower() == 'tcp':
        args.password = getpass.getpass("Enter the authentication password: ")

    # Check password strength and warn if weak
    if args.password:
        warn_weak_password(args.password)

    # TLS default: enabled for TCP unless explicitly disabled
    if not hasattr(args, 'enable_tls'):
        args.enable_tls = False
    if not hasattr(args, 'disable_tls'):
        args.disable_tls = False

    if args.protocol.lower() == 'tcp':
        if not args.disable_tls and not args.enable_tls:
            # Default to TLS enabled for TCP
            args.enable_tls = True

    return args, config_obj

def parse_server_args() -> Tuple[argparse.Namespace, Optional[configparser.ConfigParser]]:

    parser = argparse.ArgumentParser(description="PadRelay Server")
    parser.add_argument('--host', type=str, help='Host to bind to')
    parser.add_argument('--port', type=int, help='Port to listen on')
    parser.add_argument('--password', help='Authentication password')
    parser.add_argument('--gamepad-type', choices=['xbox360', 'ds4'], help='Gamepad type')
    parser.add_argument('--protocol', type=str, choices=['tcp', 'udp'], help='Transport protocol (tcp or udp)')
    parser.add_argument('--config', type=str, help='Path to configuration file (INI format)')
    parser.add_argument('--rate-limit-window', type=int, help='Rate limiting window in seconds')
    parser.add_argument('--max-requests', type=int, help='Maximum requests per window')
    parser.add_argument('--block-duration', type=int, help='Block duration in seconds when rate limit is exceeded')
    parser.add_argument(
        '--enable-tls',
        action='store_true',
        help='Enable TLS/SSL encryption (recommended for security)',
    )
    parser.add_argument(
        '--disable-tls',
        action='store_true',
        help='Disable TLS/SSL encryption (use only on trusted networks)',
    )
    parser.add_argument(
        '--cert-path',
        type=str,
        help='Path to TLS certificate file (optional, auto-generated if not provided)',
    )
    parser.add_argument(
        '--key-path',
        type=str,
        help='Path to TLS private key file (optional, auto-generated if not provided)',
    )
    args = parser.parse_args()

    env_password = os.getenv('PASSWORD')
    env_hash = os.getenv('PASSWORD_HASH')

    config_obj = None
    if args.config:
        config_obj = load_config(args.config)
        if config_obj and config_obj.has_section('server'):
            if not args.host and 'host' in config_obj['server']:
                args.host = config_obj['server']['host']
            if not args.port and 'port' in config_obj['server']:
                args.port = config_obj.getint('server', 'port')
            if not args.password and not env_password and not env_hash and 'password' in config_obj['server']:
                args.password = config_obj['server']['password']
            if not args.protocol and 'protocol' in config_obj['server']:
                args.protocol = config_obj['server']['protocol']
            if not args.rate_limit_window and 'rate_limit_window' in config_obj['server']:
                args.rate_limit_window = config_obj.getint('server', 'rate_limit_window')
            if not args.max_requests and 'max_requests' in config_obj['server']:
                args.max_requests = config_obj.getint('server', 'max_requests')
            if not args.block_duration and 'block_duration' in config_obj['server']:
                args.block_duration = config_obj.getint('server', 'block_duration')
        if config_obj and config_obj.has_section('vgamepad'):
            if not args.gamepad_type and 'type' in config_obj['vgamepad']:
                args.gamepad_type = config_obj['vgamepad']['type']

        # TLS settings
        if config_obj and config_obj.has_section('security'):
            if 'enable_tls' in config_obj['security'] and not args.enable_tls and not args.disable_tls:
                tls_enabled = config_obj.getboolean('security', 'enable_tls')
                if tls_enabled:
                    args.enable_tls = True
                else:
                    args.disable_tls = True
            if not args.cert_path and 'cert_path' in config_obj['security']:
                args.cert_path = config_obj['security']['cert_path']
            if not args.key_path and 'key_path' in config_obj['security']:
                args.key_path = config_obj['security']['key_path']

        # Convert plaintext password to hash if needed
        if (
            config_obj
            and 'password' in config_obj['server']
            and not env_password
            and not env_hash
        ):
            stored_pw = config_obj['server']['password']
            if not stored_pw.startswith('pbkdf2_sha256$'):
                hashed = Authenticator.hash_password(stored_pw)
                config_obj['server']['password'] = hashed
                args.password = hashed
                try:
                    with open(args.config, 'w') as f:
                        config_obj.write(f)
                    logger.info('Converted plaintext password to hashed password in config')
                except Exception as e:
                    logger.error(f'Failed to update config with hashed password: {e}')

    # Set defaults
    if not args.host:
        args.host = '127.0.0.1'
    if not args.port:
        args.port = 9999
    if not args.gamepad_type:
        args.gamepad_type = 'xbox360'
    if not args.protocol:
        args.protocol = 'tcp'
    if not args.rate_limit_window:
        args.rate_limit_window = DEFAULT_RATE_LIMIT_WINDOW
    if not args.max_requests:
        if args.protocol.lower() == 'udp':
            args.max_requests = DEFAULT_UDP_MAX_REQUESTS
        else:
            args.max_requests = DEFAULT_MAX_REQUESTS
    if not args.block_duration:
        args.block_duration = DEFAULT_BLOCK_DURATION
        
    # If password not provided and protocol is TCP, prompt for it
    if env_password:
        args.password = env_password
    elif env_hash:
        args.password = env_hash
    elif not args.password and args.protocol.lower() == 'tcp':
        args.password = getpass.getpass("Enter authentication password: ")

    # Check password strength and warn if weak
    if args.password:
        warn_weak_password(args.password)

    # TLS default: enabled for TCP unless explicitly disabled
    if not hasattr(args, 'enable_tls'):
        args.enable_tls = False
    if not hasattr(args, 'disable_tls'):
        args.disable_tls = False
    if not hasattr(args, 'cert_path'):
        args.cert_path = None
    if not hasattr(args, 'key_path'):
        args.key_path = None

    if args.protocol.lower() == 'tcp':
        if not args.disable_tls and not args.enable_tls:
            # Default to TLS enabled for TCP
            args.enable_tls = True

    return args, config_obj

def validate_server_config(args: argparse.Namespace, config_obj: Optional[configparser.ConfigParser]) -> None:
    """Validate the server configuration arguments"""

    if not args.host:
        raise ValueError("Host not specified.")
        
    if not (1 <= args.port <= 65535):
        raise ValueError("Port must be in range 1-65535.")
        
    if args.protocol.lower() not in ("tcp", "udp"):
        raise ValueError("Protocol must be 'tcp' or 'udp'.")
        
    if args.gamepad_type.lower() not in ("xbox360", "ds4"):
        raise ValueError("Gamepad type must be 'xbox360' or 'ds4'.")

    if args.block_duration <= 0:
        raise ValueError("Block duration must be positive.")

        
    # TCP requires password authentication
    if args.protocol.lower() == "tcp" and not args.password:
        raise ValueError("Password is required for TCP mode.")
        
    if config_obj:
        for section in ['server', 'vgamepad']:
            if not config_obj.has_section(section):
                logger.warning(f"Configuration file does not contain [{section}] section. Using default values.")
