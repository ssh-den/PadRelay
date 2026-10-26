"""The single logical input model shared by capture, protocol and output."""

from dataclasses import dataclass
from math import isfinite
from typing import Any

from ..protocol.constants import PROTOCOL_VERSION

BUTTONS = (
    "a",
    "b",
    "x",
    "y",
    "lb",
    "rb",
    "view",
    "menu",
    "guide",
    "left_stick",
    "right_stick",
    "dpad_up",
    "dpad_down",
    "dpad_left",
    "dpad_right",
)
AXES = ("left_x", "left_y", "right_x", "right_y")
TRIGGERS = ("left", "right")


@dataclass(frozen=True, slots=True)
class InputState:
    """Full snapshot: positive stick Y is up; triggers are released at zero."""

    pressed: frozenset[str] = frozenset()
    left_x: float = 0.0
    left_y: float = 0.0
    right_x: float = 0.0
    right_y: float = 0.0
    trigger_left: float = 0.0
    trigger_right: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.pressed, frozenset) or not self.pressed <= set(BUTTONS):
            raise ValueError("Invalid logical buttons")
        for name in (*AXES, "trigger_left", "trigger_right"):
            value = getattr(self, name)
            minimum = 0.0 if name.startswith("trigger_") else -1.0
            if (
                type(value) not in (int, float)
                or not isfinite(value)
                or not minimum <= value <= 1.0
            ):
                raise ValueError(f"Invalid input value: {name}")

    def to_message(self) -> dict[str, Any]:
        return {
            "type": "input",
            "protocol_version": PROTOCOL_VERSION,
            "buttons": {name: name in self.pressed for name in BUTTONS},
            "axes": {name: getattr(self, name) for name in AXES},
            "triggers": {name: getattr(self, f"trigger_{name}") for name in TRIGGERS},
        }

    @classmethod
    def from_message(cls, message: Any) -> "InputState":
        if not isinstance(message, dict) or set(message) != {
            "type",
            "protocol_version",
            "buttons",
            "axes",
            "triggers",
        }:
            raise ValueError("Expected one complete protocol-2 input snapshot")
        if (
            message["type"] != "input"
            or message["protocol_version"] != PROTOCOL_VERSION
        ):
            raise ValueError("Unsupported input version")
        for field, names in (
            ("buttons", BUTTONS),
            ("axes", AXES),
            ("triggers", TRIGGERS),
        ):
            if not isinstance(message[field], dict) or set(message[field]) != set(
                names
            ):
                raise ValueError(f"Invalid input fields: {field}")
        if not all(type(value) is bool for value in message["buttons"].values()):
            raise ValueError("Button values must be booleans")
        return cls(
            pressed=frozenset(
                name for name, value in message["buttons"].items() if value
            ),
            **message["axes"],
            **{f"trigger_{name}": value for name, value in message["triggers"].items()},
        )
