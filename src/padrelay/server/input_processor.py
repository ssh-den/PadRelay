"""Apply canonical input snapshots and expire stale input independently of heartbeat."""

import math
import time
from configparser import ConfigParser

from ..core.config import validate_controller_config
from ..core.controller_state import InputState
from .virtual_gamepad import VirtualGamepad


class GamepadHandler:
    def __init__(self, gamepad: VirtualGamepad, config: ConfigParser | None = None):
        self.gamepad = gamepad
        validate_controller_config(config)
        self.input_timeout = (
            config.getfloat("server", "input_timeout", fallback=1.0) if config else 1.0
        )
        if not math.isfinite(self.input_timeout) or not 0.1 <= self.input_timeout <= 10:
            raise ValueError("input_timeout must be between 0.1 and 10 seconds")
        self.last_state: InputState | None = None
        self.last_received: float | None = None
        self._reset_pending = False

    def reset(self) -> None:
        self.last_state = None
        self._reset_pending = True
        self.gamepad.reset_gamepad_state()
        self._reset_pending = False
        self.last_received = None

    def process(self, message: dict) -> None:
        state = InputState.from_message(message)
        if state != self.last_state:
            self.last_state = None
            self._reset_pending = True
            self.gamepad.apply_state(state)
            self.last_state = state
            self._reset_pending = False
        self.last_received = time.monotonic()

    def expire_input(self) -> None:
        if (
            self._reset_pending
            or self.last_received is not None
            and time.monotonic() - self.last_received >= self.input_timeout
        ):
            self.reset()
