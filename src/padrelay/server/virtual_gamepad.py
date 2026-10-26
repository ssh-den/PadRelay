"""The only adapter that knows vgamepad/ViGEm target details."""

from configparser import ConfigParser
from typing import Any

from ..core.config import validate_controller_config
from ..core.controller_state import InputState

XBOX_BUTTONS = {
    "a": "A",
    "b": "B",
    "x": "X",
    "y": "Y",
    "lb": "LEFT_SHOULDER",
    "rb": "RIGHT_SHOULDER",
    "view": "BACK",
    "menu": "START",
    "guide": "GUIDE",
    "left_stick": "LEFT_THUMB",
    "right_stick": "RIGHT_THUMB",
    "dpad_up": "DPAD_UP",
    "dpad_down": "DPAD_DOWN",
    "dpad_left": "DPAD_LEFT",
    "dpad_right": "DPAD_RIGHT",
}
DS4_BUTTONS = {
    "a": "CROSS",
    "b": "CIRCLE",
    "x": "SQUARE",
    "y": "TRIANGLE",
    "lb": "SHOULDER_LEFT",
    "rb": "SHOULDER_RIGHT",
    "view": "SHARE",
    "menu": "OPTIONS",
    "left_stick": "THUMB_LEFT",
    "right_stick": "THUMB_RIGHT",
}
DPAD = {
    (0, 0): "NONE",
    (0, 1): "NORTH",
    (1, 1): "NORTHEAST",
    (1, 0): "EAST",
    (1, -1): "SOUTHEAST",
    (0, -1): "SOUTH",
    (-1, -1): "SOUTHWEST",
    (-1, 0): "WEST",
    (-1, 1): "NORTHWEST",
}


class VirtualGamepad:
    def __init__(
        self, gamepad_type: str = "xbox360", config: ConfigParser | None = None
    ):
        if gamepad_type not in ("xbox360", "ds4"):
            raise ValueError("Unknown virtual target")
        validate_controller_config(config)
        import vgamepad as vg  # pyright: ignore[reportMissingImports]

        self.vg = vg
        self.gamepad_type = gamepad_type
        self.gamepad: Any = (
            vg.VDS4Gamepad() if gamepad_type == "ds4" else vg.VX360Gamepad()
        )
        self.reset_gamepad_state()

    def reset_gamepad_state(self) -> None:
        self.gamepad.reset()
        self.gamepad.update()

    def apply_state(self, state: InputState) -> None:
        ds4 = self.gamepad_type == "ds4"
        names = DS4_BUTTONS if ds4 else XBOX_BUTTONS
        enum = self.vg.DS4_BUTTONS if ds4 else self.vg.XUSB_BUTTON
        prefix = "DS4_BUTTON_" if ds4 else "XUSB_GAMEPAD_"
        # Write a complete report so releases never depend on a previous cache.
        for name, suffix in names.items():
            method = (
                self.gamepad.press_button
                if name in state.pressed
                else self.gamepad.release_button
            )
            method(button=getattr(enum, prefix + suffix))
        if ds4:
            method = (
                self.gamepad.press_special_button
                if "guide" in state.pressed
                else self.gamepad.release_special_button
            )
            method(special_button=self.vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)
            x = int("dpad_right" in state.pressed) - int("dpad_left" in state.pressed)
            y = int("dpad_up" in state.pressed) - int("dpad_down" in state.pressed)
            self.gamepad.directional_pad(
                direction=getattr(
                    self.vg.DS4_DPAD_DIRECTIONS, "DS4_BUTTON_DPAD_" + DPAD[x, y]
                )
            )
        self.gamepad.left_joystick_float(
            x_value_float=state.left_x,
            y_value_float=-state.left_y if ds4 else state.left_y,
        )
        self.gamepad.right_joystick_float(
            x_value_float=state.right_x,
            y_value_float=-state.right_y if ds4 else state.right_y,
        )
        self.gamepad.left_trigger_float(value_float=state.trigger_left)
        self.gamepad.right_trigger_float(value_float=state.trigger_right)
        self.gamepad.update()
