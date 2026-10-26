from configparser import ConfigParser
from unittest.mock import Mock

import pytest

from padrelay.core.controller_state import InputState
from padrelay.server import input_processor


def test_complete_state_cache_and_reset():
    gamepad = Mock()
    handler = input_processor.GamepadHandler(gamepad)
    state = InputState(frozenset({"a"}), left_x=0.5)
    handler.process(state.to_message())
    handler.process(state.to_message())
    gamepad.apply_state.assert_called_once_with(state)
    handler.reset()
    handler.process(state.to_message())
    assert gamepad.apply_state.call_count == 2
    gamepad.reset_gamepad_state.assert_called_once()


def test_trigger_changes_without_stick_changes():
    gamepad = Mock()
    handler = input_processor.GamepadHandler(gamepad)
    handler.process(InputState().to_message())
    state = InputState(trigger_left=0.8)
    handler.process(state.to_message())
    gamepad.apply_state.assert_called_with(state)


def test_failed_native_write_is_not_cached_as_applied():
    gamepad = Mock()
    gamepad.apply_state.side_effect = RuntimeError("Native driver unavailable")
    handler = input_processor.GamepadHandler(gamepad)
    packet = InputState(frozenset({"a"})).to_message()
    with pytest.raises(RuntimeError):
        handler.process(packet)
    assert handler.last_state is None and handler.last_received is None
    gamepad.apply_state.side_effect = None
    handler.process(packet)
    assert gamepad.apply_state.call_count == 2


def test_failed_reset_invalidates_cache_and_watchdog_retries(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(input_processor.time, "monotonic", lambda: clock[0])
    gamepad = Mock()
    handler = input_processor.GamepadHandler(gamepad)
    packet = InputState(frozenset({"a"})).to_message()
    handler.process(packet)
    clock[0] = 2.0
    gamepad.reset_gamepad_state.side_effect = [OSError("driver failure"), None]
    with pytest.raises(OSError):
        handler.expire_input()
    assert handler.last_state is None and handler.last_received == 0.0
    handler.expire_input()
    assert gamepad.reset_gamepad_state.call_count == 2
    assert handler.last_received is None
    handler.process(packet)
    assert gamepad.apply_state.call_count == 2


def test_same_state_is_reapplied_after_failed_reset():
    gamepad = Mock()
    handler = input_processor.GamepadHandler(gamepad)
    packet = InputState(frozenset({"a"})).to_message()
    handler.process(packet)
    gamepad.reset_gamepad_state.side_effect = OSError("driver failure")
    with pytest.raises(OSError):
        handler.reset()
    handler.process(packet)
    assert gamepad.apply_state.call_count == 2


def test_reset_failure_before_first_input_is_retried():
    gamepad = Mock()
    gamepad.reset_gamepad_state.side_effect = [OSError("driver failure"), None]
    handler = input_processor.GamepadHandler(gamepad)
    with pytest.raises(OSError):
        handler.reset()
    assert handler.last_received is None
    handler.expire_input()
    handler.expire_input()
    assert gamepad.reset_gamepad_state.call_count == 2


def test_failed_first_write_schedules_watchdog_reset():
    gamepad = Mock()
    gamepad.apply_state.side_effect = OSError("partial report failure")
    handler = input_processor.GamepadHandler(gamepad)
    with pytest.raises(OSError):
        handler.process(InputState(frozenset({"a"})).to_message())
    handler.expire_input()
    gamepad.reset_gamepad_state.assert_called_once()


def test_failed_report_invalidates_previous_cache():
    gamepad = Mock()
    handler = input_processor.GamepadHandler(gamepad)
    previous = InputState(frozenset({"a"})).to_message()
    handler.process(previous)
    gamepad.apply_state.side_effect = [OSError("partial report failure"), None]
    with pytest.raises(OSError):
        handler.process(InputState(frozenset({"b"})).to_message())
    handler.process(previous)
    assert gamepad.apply_state.call_count == 3
    handler.expire_input()
    gamepad.reset_gamepad_state.assert_not_called()


def test_watchdog_uses_received_frames_not_changed_frames(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(input_processor.time, "monotonic", lambda: clock[0])
    gamepad = Mock()
    handler = input_processor.GamepadHandler(gamepad)
    packet = InputState(frozenset({"a"})).to_message()
    handler.process(packet)
    clock[0] = 0.9
    handler.process(packet)
    clock[0] = 1.1
    handler.expire_input()
    gamepad.reset_gamepad_state.assert_not_called()
    clock[0] = 2.0
    handler.expire_input()
    handler.expire_input()
    gamepad.reset_gamepad_state.assert_called_once()
    handler.process(packet)
    assert gamepad.apply_state.call_count == 2


@pytest.mark.parametrize(
    "section",
    [
        "axis_mapping",
        "axis_options",
        "button_mapping_xbox360",
        "button_mapping_ds4_hat",
    ],
)
def test_old_physical_server_maps_are_rejected(section):
    config = ConfigParser()
    config[section] = {}
    with pytest.raises(ValueError, match="client JSON"):
        input_processor.GamepadHandler(Mock(), config)


@pytest.mark.parametrize("value", ["nan", "inf", "0", "100"])
def test_watchdog_configuration_is_bounded(value):
    config = ConfigParser()
    config["server"] = {"input_timeout": value}
    with pytest.raises(ValueError):
        input_processor.GamepadHandler(Mock(), config)
