from types import SimpleNamespace
from unittest.mock import Mock

import pygame
import pytest

from padrelay.client import input as capture
from padrelay.client.controller_profile import (
    CONTROLS,
    ControllerProfile,
    DeviceIdentity,
)
from padrelay.core.controller_state import AXES, BUTTONS, InputState


@pytest.fixture
def hardware(monkeypatch):
    joystick = Mock()
    joystick.get_guid.return_value = "030082795e040000200b000011056800"
    joystick.get_name.return_value = "Xbox One S Controller"
    joystick.get_numaxes.return_value = 6
    joystick.get_numbuttons.return_value = 15
    joystick.get_numhats.return_value = 1
    joystick.get_instance_id.return_value = 7
    joystick.get_axis.side_effect = lambda i: [0.07, 0.01, 0.02, 0.07, -1.0, -1.0][i]
    joystick.get_button.return_value = False
    joystick.get_hat.return_value = (0, 0)
    controller = Mock()
    controller.attached.return_value = True
    controller.axes = {i: 0 for i in range(6)}
    controller.buttons = set()
    controller.get_axis.side_effect = lambda i: controller.axes[i]
    controller.get_button.side_effect = lambda i: i in controller.buttons
    devices = [joystick]
    clock = [0.0]
    monkeypatch.setattr(capture, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(pygame, "init", lambda: None)
    monkeypatch.setattr(pygame, "quit", Mock())
    monkeypatch.setattr(pygame.event, "get", lambda: [])
    monkeypatch.setattr(pygame.joystick, "init", lambda: None)
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: len(devices))
    monkeypatch.setattr(pygame.joystick, "Joystick", lambda i: devices[i])
    monkeypatch.setattr(capture.sdl_controller, "init", lambda: None)
    monkeypatch.setattr(capture.sdl_controller, "is_controller", lambda i: True)
    factory = Mock(return_value=controller)
    monkeypatch.setattr(
        capture.sdl_controller, "Controller", SimpleNamespace(from_joystick=factory)
    )
    return SimpleNamespace(
        joystick=joystick,
        controller=controller,
        devices=devices,
        clock=clock,
        factory=factory,
    )


def test_no_raw_inputs_or_duplicate_payload(hardware):
    reader = capture.GamepadInput()
    assert reader.initialize()
    hardware.controller.axes[pygame.CONTROLLER_AXIS_TRIGGERLEFT] = 32767
    state = InputState.from_message(reader.poll())
    assert state.trigger_left == 1.0 and state.right_x == 0
    hardware.joystick.get_axis.assert_not_called()
    hardware.joystick.get_button.assert_not_called()
    assert set(reader.poll()) == {
        "type",
        "protocol_version",
        "buttons",
        "axes",
        "triggers",
    }


def test_sdl_binding_table_covers_the_wire_contract():
    assert set(capture.SDL_BUTTONS) == set(BUTTONS)
    assert set(capture.SDL_AXES) == set(AXES)


def test_lt_does_not_follow_right_stick(hardware):
    reader = capture.GamepadInput()
    assert reader.initialize()
    hardware.controller.axes[pygame.CONTROLLER_AXIS_RIGHTX] = 32767
    state = InputState.from_message(reader.poll())
    assert state.right_x == 1 and state.trigger_left == 0


@pytest.mark.parametrize("logical,sdl", list(capture.SDL_BUTTONS.items()))
def test_all_logical_buttons(hardware, logical, sdl):
    reader = capture.GamepadInput()
    assert reader.initialize()
    hardware.controller.buttons.add(getattr(pygame, f"CONTROLLER_BUTTON_{sdl}"))
    assert InputState.from_message(reader.poll()).pressed == frozenset({logical})


def test_limits_y_and_dead_zone(hardware):
    reader = capture.GamepadInput()
    assert reader.initialize()
    hardware.controller.axes.update(
        {
            pygame.CONTROLLER_AXIS_LEFTY: -32768,
            pygame.CONTROLLER_AXIS_RIGHTX: 100,
            pygame.CONTROLLER_AXIS_TRIGGERLEFT: 32768,
        }
    )
    state = InputState.from_message(reader.poll())
    assert state.left_y == 1 and state.right_x == 0 and state.trigger_left == 1


def test_reconnect_by_identity_after_index_changes(hardware):
    reader = capture.GamepadInput()
    assert reader.initialize()
    hardware.controller.attached.return_value = False
    assert reader.poll() is None
    other = Mock(wraps=hardware.joystick)
    other.get_guid.return_value = "different"
    other.get_name.return_value = "Different device"
    hardware.devices[:] = [other, hardware.joystick]
    hardware.controller.attached.return_value = True
    hardware.clock[0] = 1
    assert reader.poll() is not None
    assert hardware.factory.call_count == 2
    assert reader.identity.guid == hardware.joystick.get_guid()


def test_ambiguous_reconnect_never_selects_first(hardware):
    reader = capture.GamepadInput()
    assert reader.initialize()
    hardware.controller.attached.return_value = False
    assert reader.poll() is None
    hardware.devices[:] = [hardware.joystick, hardware.joystick]
    hardware.clock[0] = 1
    assert not reader.is_available()
    assert hardware.factory.call_count == 1


def test_start_without_controller_then_connect(hardware):
    hardware.devices.clear()
    reader = capture.GamepadInput()
    assert reader.initialize()
    assert not reader.is_available()
    hardware.devices.append(hardware.joystick)
    hardware.clock[0] = 1
    assert reader.is_available()


def test_unknown_device_requires_profile_even_if_named_xbox(hardware, monkeypatch):
    monkeypatch.setattr(capture.sdl_controller, "is_controller", lambda i: False)
    reader = capture.GamepadInput()
    assert not reader.initialize()


def test_profile_mismatch_is_not_ignored(hardware, tmp_path):
    identity = DeviceIdentity(
        "another-guid", "Another controller", "unknown-platform", 15, 6, 1
    )
    path = tmp_path / "profile.json"
    ControllerProfile(identity, dict.fromkeys(CONTROLS)).save(path)
    assert not capture.GamepadInput(profile_path=path).initialize()


def test_profile_path_is_exclusive_raw_capture(hardware, tmp_path):
    bindings = dict.fromkeys(CONTROLS)
    bindings["lb"] = dict(kind="button", index=9)
    bindings["trigger_left"] = dict(kind="axis", index=4, rest=-1.0, end=1.0)
    path = tmp_path / "profile.json"
    ControllerProfile(DeviceIdentity.read(hardware.joystick), bindings).save(path)
    hardware.joystick.get_button.side_effect = lambda i: i == 9
    hardware.joystick.get_axis.return_value = 1.0
    hardware.joystick.get_axis.side_effect = None
    reader = capture.GamepadInput(profile_path=path)
    assert reader.initialize()
    state = InputState.from_message(reader.poll())
    assert state.pressed == frozenset({"lb"}) and state.trigger_left == 1
    hardware.factory.assert_not_called()


def test_device_removed_event_ends_profile_capture(hardware, tmp_path, monkeypatch):
    path = tmp_path / "profile.json"
    ControllerProfile(
        DeviceIdentity.read(hardware.joystick), dict.fromkeys(CONTROLS)
    ).save(path)
    reader = capture.GamepadInput(profile_path=path)
    assert reader.initialize()
    monkeypatch.setattr(
        pygame.event,
        "get",
        lambda: [SimpleNamespace(type=pygame.JOYDEVICEREMOVED, instance_id=7)],
    )
    assert reader.poll() is None


def test_cleanup_closes_native_handles(hardware):
    reader = capture.GamepadInput()
    assert reader.initialize()
    reader.cleanup()
    hardware.controller.quit.assert_called_once()
    hardware.joystick.quit.assert_called_once()
    assert not reader.is_available()
