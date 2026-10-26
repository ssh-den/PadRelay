"""Physical device lifecycle and client-side normalization."""

import time
from pathlib import Path
from typing import Any

import pygame
from pygame._sdl2 import controller as sdl_controller

from ..core.controller_state import InputState
from ..core.logging_utils import get_logger
from .controller_profile import ControllerProfile, DeviceIdentity

logger = get_logger(__name__)
SDL_BUTTONS = {
    "a": "A",
    "b": "B",
    "x": "X",
    "y": "Y",
    "lb": "LEFTSHOULDER",
    "rb": "RIGHTSHOULDER",
    "view": "BACK",
    "menu": "START",
    "guide": "GUIDE",
    "left_stick": "LEFTSTICK",
    "right_stick": "RIGHTSTICK",
    "dpad_up": "DPAD_UP",
    "dpad_down": "DPAD_DOWN",
    "dpad_left": "DPAD_LEFT",
    "dpad_right": "DPAD_RIGHT",
}
SDL_AXES = {
    "left_x": "LEFTX",
    "left_y": "LEFTY",
    "right_x": "RIGHTX",
    "right_y": "RIGHTY",
}


class GamepadInput:
    """One selected device; profiles and reconnect identity belong to this instance."""

    def __init__(self, joystick_index: int = 0, profile_path: Path | None = None):
        if joystick_index < 0:
            raise ValueError("Joystick index must be nonnegative")
        self.joystick_index = joystick_index
        self.profile = ControllerProfile.load(profile_path) if profile_path else None
        self.identity: DeviceIdentity | None = None
        self.joystick: Any = None
        self.controller: Any = None
        self.initialized = False
        self._next_scan = 0.0
        self._instance_id: int | None = None

    def initialize(self) -> bool:
        try:
            pygame.init()
            pygame.joystick.init()
            if self.profile is None:
                sdl_controller.init()
            self.initialized = True
            if pygame.joystick.get_count() > self.joystick_index:
                self._open(self.joystick_index)
            else:
                logger.info("Waiting for controller index %s", self.joystick_index)
            return True
        except (pygame.error, ValueError) as exc:
            logger.error("Cannot initialize controller: %s", exc)
            self.cleanup()
            return False

    def _open(self, index: int) -> None:
        joystick = pygame.joystick.Joystick(index)
        joystick.init()
        identity = DeviceIdentity.read(joystick)
        try:
            if self.profile is not None and identity != self.profile.identity:
                raise ValueError(
                    "Controller profile does not match this device/OS/driver layout"
                )
            if self.profile is None:
                if not sdl_controller.is_controller(index):
                    raise ValueError(
                        "Unrecognized controller; create a profile with padrelay-keymapper"
                    )
                self.controller = sdl_controller.Controller.from_joystick(joystick)
            self.joystick = joystick
            self.identity = identity
            self._instance_id = joystick.get_instance_id()
            logger.info("Controller connected: %s (%s)", identity.name, identity.guid)
        except Exception:
            joystick.quit()
            raise

    def _detach(self) -> None:
        for handle in (self.controller, self.joystick):
            if handle is not None:
                try:
                    handle.quit()
                except pygame.error:
                    pass
        self.controller = self.joystick = None
        self._instance_id = None
        self._next_scan = time.monotonic() + 0.25

    def is_available(self) -> bool:
        if not self.initialized:
            return False
        try:
            for event in pygame.event.get():
                if (
                    event.type == pygame.JOYDEVICEREMOVED
                    and event.instance_id == self._instance_id
                ):
                    self._detach()
            if self.controller is not None and not self.controller.attached():
                self._detach()
            if self.joystick is not None:
                return True
            if time.monotonic() < self._next_scan:
                return False
            self._next_scan = time.monotonic() + 0.25
            if self.identity is None:
                if pygame.joystick.get_count() > self.joystick_index:
                    self._open(self.joystick_index)
            else:
                matches = []
                for index in range(pygame.joystick.get_count()):
                    candidate = pygame.joystick.Joystick(index)
                    candidate.init()
                    try:
                        if DeviceIdentity.read(candidate) == self.identity:
                            matches.append(index)
                    finally:
                        candidate.quit()
                if len(matches) == 1:
                    self._open(matches[0])
                elif len(matches) > 1:
                    logger.warning(
                        "Ambiguous reconnect: select one device explicitly and restart"
                    )
            return self.joystick is not None
        except (pygame.error, ValueError) as exc:
            logger.warning("Controller unavailable: %s", exc)
            self._detach()
            return False

    def poll(self) -> dict | None:
        if not self.is_available():
            return None
        try:
            if self.profile is not None:
                state = self.profile.read(self.joystick)
            else:
                pressed = frozenset(
                    name
                    for name, sdl_name in SDL_BUTTONS.items()
                    if self.controller.get_button(
                        getattr(pygame, f"CONTROLLER_BUTTON_{sdl_name}")
                    )
                )
                values = {}
                for name, sdl_name in SDL_AXES.items():
                    value = (
                        self.controller.get_axis(
                            getattr(pygame, f"CONTROLLER_AXIS_{sdl_name}")
                        )
                        / 32767.0
                    )
                    value = max(-1.0, min(1.0, value))
                    if name.endswith("_y"):
                        value = -value
                    values[name] = value if abs(value) > 0.1 else 0.0
                for side in ("left", "right"):
                    value = (
                        self.controller.get_axis(
                            getattr(pygame, f"CONTROLLER_AXIS_TRIGGER{side.upper()}")
                        )
                        / 32767.0
                    )
                    values[f"trigger_{side}"] = (
                        max(0.0, min(1.0, value)) if value > 0.05 else 0.0
                    )
                state = InputState(pressed, **values)
            return state.to_message()
        except (pygame.error, ValueError) as exc:
            logger.warning("Controller read failed: %s", exc)
            self._detach()
            return None

    def cleanup(self) -> None:
        self._detach()
        pygame.quit()
        self.initialized = False
