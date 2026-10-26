import json

import pytest

from padrelay.core.controller_state import InputState
from padrelay.protocol.messages import BaseMessage, InputMessage, validate_input_message


def test_message_serialization_roundtrip():
    state = InputState(frozenset({"a", "dpad_up"}), left_x=0.5, trigger_right=1.0)
    message = InputMessage(state)
    parsed = BaseMessage.from_dict(json.loads(message.to_bytes()))
    assert isinstance(parsed, InputMessage)
    assert InputState.from_message(parsed.data) == state
    assert set(parsed.data) == {
        "type",
        "protocol_version",
        "buttons",
        "axes",
        "triggers",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("buttons", []),
        ("axes", []),
        ("triggers", []),
        ("buttons", {"a": True}),
        ("axes", {"left_x": 0}),
        ("triggers", {"left": 0}),
        ("protocol_version", "1.0"),
        ("type", "heartbeat"),
        ("controller", {}),
        ("hats", [[0, 1]]),
        ("timestamp", "ignored"),
    ],
)
def test_incomplete_legacy_or_duplicated_state_is_rejected(field, value):
    packet = InputState().to_message()
    packet[field] = value
    assert not validate_input_message(packet)


@pytest.mark.parametrize(
    "value", [True, "1", None, float("nan"), float("inf"), -1.1, 1.1]
)
def test_invalid_axis_values(value):
    packet = InputState().to_message()
    packet["axes"]["left_x"] = value
    assert not validate_input_message(packet)


@pytest.mark.parametrize("value", [-0.1, 1.1, True, float("nan")])
def test_invalid_trigger_values(value):
    packet = InputState().to_message()
    packet["triggers"]["left"] = value
    assert not validate_input_message(packet)


def test_full_neutral_is_valid_and_false_is_not_a_numeric_axis():
    packet = InputState().to_message()
    assert validate_input_message(packet)
    packet["buttons"]["a"] = 1
    assert not validate_input_message(packet)
