import types
import sys

import pytest


class DummyEnum:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class DummyGamepad:
    def __init__(self):
        self.reset_called = False
        self.updated = False

    def reset(self):
        self.reset_called = True

    def update(self):
        self.updated = True

    # Stub methods used by GamepadHandler
    def press_button(self, button):
        pass

    def release_button(self, button):
        pass

    def left_joystick_float(self, **kwargs):
        pass

    def right_joystick_float(self, **kwargs):
        pass

    def left_trigger_float(self, **kwargs):
        pass

    def right_trigger_float(self, **kwargs):
        pass


class DummyVG:
    XUSB_BUTTON = DummyEnum(XUSB_GAMEPAD_A=1, XUSB_GAMEPAD_B=2, XUSB_GAMEPAD_X=3, XUSB_GAMEPAD_Y=4,
                            XUSB_GAMEPAD_LEFT_SHOULDER=5, XUSB_GAMEPAD_RIGHT_SHOULDER=6,
                            XUSB_GAMEPAD_BACK=7, XUSB_GAMEPAD_START=8, XUSB_GAMEPAD_LEFT_THUMB=9,
                            XUSB_GAMEPAD_RIGHT_THUMB=10, XUSB_GAMEPAD_DPAD_UP=11, XUSB_GAMEPAD_DPAD_DOWN=12,
                            XUSB_GAMEPAD_DPAD_LEFT=13, XUSB_GAMEPAD_DPAD_RIGHT=14, XUSB_GAMEPAD_GUIDE=15)
    DS4_BUTTONS = DummyEnum(DS4_BUTTON_CROSS=1, DS4_BUTTON_CIRCLE=2, DS4_BUTTON_SQUARE=3,
                            DS4_BUTTON_TRIANGLE=4, DS4_BUTTON_SHOULDER_LEFT=5, DS4_BUTTON_SHOULDER_RIGHT=6,
                            DS4_BUTTON_SHARE=7, DS4_BUTTON_OPTIONS=8, DS4_BUTTON_THUMB_LEFT=9,
                            DS4_BUTTON_THUMB_RIGHT=10, DS4_BUTTON_TRIGGER_LEFT=11, DS4_BUTTON_TRIGGER_RIGHT=12)

    class VX360Gamepad(DummyGamepad):
        pass

    class VDS4Gamepad(DummyGamepad):
        pass


def test_default_button_mapping(monkeypatch):
    sys.modules['vgamepad'] = DummyVG()
    from padrelay.server.virtual_gamepad import VirtualGamepad

    vg = VirtualGamepad('xbox360')
    mapping = vg.get_button_mapping()
    assert 0 in mapping and mapping[0] == DummyVG.XUSB_BUTTON.XUSB_GAMEPAD_A

    vg_ds4 = VirtualGamepad('ds4')
    mapping_ds4 = vg_ds4.get_button_mapping()
    assert 0 in mapping_ds4 and mapping_ds4[0] == DummyVG.DS4_BUTTONS.DS4_BUTTON_CROSS
