"""Validated physical bindings and atomic, device-bound profile persistence."""

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from ..core.controller_state import AXES, BUTTONS, InputState

CONTROLS = (*BUTTONS, *AXES, "trigger_left", "trigger_right")
HAT_DIRECTIONS = {"up": (1, 1), "down": (1, -1), "left": (0, -1), "right": (0, 1)}


@dataclass(frozen=True)
class DeviceIdentity:
    guid: str
    name: str
    platform: str
    buttons: int
    axes: int
    hats: int

    def __post_init__(self) -> None:
        if not all(
            isinstance(v, str) and v for v in (self.guid, self.name, self.platform)
        ):
            raise ValueError("Invalid device identity")
        if not all(
            type(v) is int and 0 <= v <= 256
            for v in (self.buttons, self.axes, self.hats)
        ):
            raise ValueError("Invalid device capabilities")

    @classmethod
    def read(cls, joystick: Any) -> "DeviceIdentity":
        return cls(
            joystick.get_guid(),
            joystick.get_name(),
            sys.platform,
            joystick.get_numbuttons(),
            joystick.get_numaxes(),
            joystick.get_numhats(),
        )


class ControllerProfile:
    """Own a validated copy of bindings; no caller can mutate the live profile."""

    def __init__(
        self,
        identity: DeviceIdentity,
        bindings: dict,
        dead_zone: float = 0.1,
        trigger_threshold: float = 0.05,
    ):
        self.identity = identity
        if not isinstance(bindings, dict):
            raise ValueError("Profile bindings must be an object")
        self._bindings = json.loads(json.dumps(bindings, allow_nan=False))
        if set(self._bindings) != set(CONTROLS):
            raise ValueError(
                "Profile must explicitly map or skip every logical control"
            )
        for value in (dead_zone, trigger_threshold):
            if (
                type(value) not in (int, float)
                or not isfinite(value)
                or not 0 <= value < 1
            ):
                raise ValueError("Invalid calibration threshold")
        self.dead_zone = dead_zone
        self.trigger_threshold = trigger_threshold
        for name, binding in self._bindings.items():
            self._validate_binding(name, binding)

    def _validate_binding(self, name: str, binding: Any) -> None:
        if binding is None:
            return
        if not isinstance(binding, dict):
            raise ValueError(f"Invalid binding: {name}")
        kind = binding.get("kind")
        fields = {
            "button": {"kind", "index"},
            "hat": {"kind", "index", "direction"},
            "axis": {"kind", "index", "rest", "end"}
            | ({"opposite"} if name in AXES else set()),
        }
        if kind not in fields or set(binding) != fields[kind]:
            raise ValueError(f"Invalid binding fields: {name}")
        if (name in BUTTONS) != (kind in ("button", "hat")):
            raise ValueError(f"Wrong binding type: {name}")
        count = getattr(
            self.identity, {"button": "buttons", "hat": "hats", "axis": "axes"}[kind]
        )
        index = binding["index"]
        if type(index) is not int or not 0 <= index < count:
            raise ValueError(f"Binding index out of range: {name}")
        if kind == "hat" and binding["direction"] not in HAT_DIRECTIONS:
            raise ValueError("Invalid hat direction")
        if kind == "axis":
            if (
                not all(
                    type(binding[k]) in (int, float)
                    and isfinite(binding[k])
                    and -1 <= binding[k] <= 1
                    for k in fields["axis"] - {"kind", "index"}
                )
                or abs(binding["end"] - binding["rest"]) < 0.3
            ):
                raise ValueError(f"Invalid axis calibration: {name}")
            if name in AXES and (
                abs(binding["opposite"] - binding["rest"]) < 0.3
                or (binding["opposite"] - binding["rest"])
                * (binding["end"] - binding["rest"])
                >= 0
            ):
                raise ValueError(f"Stick endpoints must straddle neutral: {name}")

    def read(self, joystick: Any) -> InputState:
        pressed = set()
        values = {}
        for name, binding in self._bindings.items():
            if binding is None:
                continue
            index = binding["index"]
            if binding["kind"] == "button":
                if joystick.get_button(index):
                    pressed.add(name)
            elif binding["kind"] == "hat":
                coordinate, value = HAT_DIRECTIONS[binding["direction"]]
                if joystick.get_hat(index)[coordinate] == value:
                    pressed.add(name)
            else:
                displacement = joystick.get_axis(index) - binding["rest"]
                span = binding["end"] - binding["rest"]
                if name in AXES and displacement * span < 0:
                    span = binding["rest"] - binding["opposite"]
                value = displacement / span
                threshold = (
                    self.trigger_threshold
                    if name.startswith("trigger_")
                    else self.dead_zone
                )
                minimum = 0.0 if name.startswith("trigger_") else -1.0
                values[name] = (
                    max(minimum, min(1.0, value)) if abs(value) > threshold else 0.0
                )
        return InputState(pressed=frozenset(pressed), **values)

    def save(self, path: Path) -> None:
        data = dict(
            version=1,
            device=asdict(self.identity),
            bindings=self._bindings,
            dead_zone=self.dead_zone,
            trigger_threshold=self.trigger_threshold,
        )
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2, allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @classmethod
    def load(cls, path: Path) -> "ControllerProfile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if (
            not isinstance(data, dict)
            or set(data)
            != {"version", "device", "bindings", "dead_zone", "trigger_threshold"}
            or type(data["version"]) is not int
            or data["version"] != 1
        ):
            raise ValueError("Unsupported controller profile")
        try:
            return cls(
                DeviceIdentity(**data["device"]),
                data["bindings"],
                data["dead_zone"],
                data["trigger_threshold"],
            )
        except (TypeError, KeyError) as exc:
            raise ValueError("Invalid controller profile") from exc
