from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from padrelay.core.controller_state import InputState
from padrelay.server.virtual_gamepad import (
    DPAD,
    DS4_BUTTONS,
    XBOX_BUTTONS,
    VirtualGamepad,
)


class Names:
    def __getattr__(self, name):
        return name


def virtual(target):
    adapter = VirtualGamepad.__new__(VirtualGamepad)
    adapter.gamepad_type = target
    adapter.gamepad = Mock()
    adapter.vg = SimpleNamespace(
        XUSB_BUTTON=Names(),
        DS4_BUTTONS=Names(),
        DS4_SPECIAL_BUTTONS=Names(),
        DS4_DPAD_DIRECTIONS=Names(),
    )
    return adapter


@pytest.mark.parametrize("target", ["xbox360", "ds4"])
def test_all_buttons_and_releases(target):
    adapter = virtual(target)
    mapping = DS4_BUTTONS if target == "ds4" else XBOX_BUTTONS
    adapter.apply_state(InputState(frozenset(mapping)))
    assert adapter.gamepad.press_button.call_count == len(mapping)
    adapter.gamepad.reset_mock()
    adapter.apply_state(InputState())
    assert adapter.gamepad.release_button.call_count == len(mapping)
    adapter.gamepad.press_button.assert_not_called()


@pytest.mark.parametrize("x,y", list(DPAD))
def test_ds4_hat_all_directions_and_neutral(x, y):
    pressed = set()
    if x:
        pressed.add("dpad_right" if x > 0 else "dpad_left")
    if y:
        pressed.add("dpad_up" if y > 0 else "dpad_down")
    adapter = virtual("ds4")
    adapter.apply_state(InputState(frozenset(pressed)))
    adapter.gamepad.directional_pad.assert_called_once_with(
        direction="DS4_BUTTON_DPAD_" + DPAD[x, y]
    )


def test_ds4_guide_uses_special_api_and_opposite_hat_cancels():
    adapter = virtual("ds4")
    adapter.apply_state(InputState(frozenset({"guide", "dpad_up", "dpad_down"})))
    adapter.gamepad.press_special_button.assert_called_once_with(
        special_button="DS4_SPECIAL_BUTTON_PS"
    )
    adapter.gamepad.directional_pad.assert_called_with(direction="DS4_BUTTON_DPAD_NONE")
    adapter.apply_state(InputState())
    adapter.gamepad.release_special_button.assert_called_with(
        special_button="DS4_SPECIAL_BUTTON_PS"
    )


@pytest.mark.parametrize("target,y", [("xbox360", 1.0), ("ds4", -1.0)])
def test_target_coordinates_and_analog_triggers(target, y):
    adapter = virtual(target)
    adapter.apply_state(InputState(left_y=1.0, trigger_left=1.0))
    adapter.gamepad.left_joystick_float.assert_called_once_with(
        x_value_float=0.0, y_value_float=y
    )
    adapter.gamepad.left_trigger_float.assert_called_once_with(value_float=1.0)
