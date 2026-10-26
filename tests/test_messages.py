import pytest
from padrelay.protocol.messages import (
    BaseMessage,
    InputMessage,
    HeartbeatMessage,
    HeartbeatAckMessage,
    AuthChallengeMessage,
    AuthResponseMessage,
    AuthSuccessMessage,
    AuthFailedMessage,
    ErrorMessage,
    validate_input_message,
)


def test_message_serialization_roundtrip():
    msg = InputMessage(buttons=[True, False], axes=[0.0, 1.0], hats=[(0, 1)])
    json_data = msg.to_json()
    msg_bytes = msg.to_bytes()
    assert isinstance(json_data, str)
    assert isinstance(msg_bytes, bytes)

    # Deserialize using BaseMessage.from_dict
    parsed = BaseMessage.from_dict(msg.data)
    assert isinstance(parsed, InputMessage)
    assert parsed.data["buttons"] == [True, False]


def test_validate_input_message():
    valid = {
        "type": "input",
        "buttons": [True, False],
        "axes": [0.0, 0.5],
        "hats": [(0, 1)],
    }
    assert validate_input_message(valid)

    invalid = {"type": "input", "buttons": ["bad"]}
    assert not validate_input_message(invalid)
