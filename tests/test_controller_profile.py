import json
from unittest.mock import Mock

import pytest

from padrelay.client.controller_profile import (
    CONTROLS,
    ControllerProfile,
    DeviceIdentity,
)

IDENTITY = DeviceIdentity("guid", "Test controller", "test", 15, 6, 1)


def test_profile_atomic_roundtrip_and_isolated_bindings(tmp_path):
    bindings = dict.fromkeys(CONTROLS)
    bindings["a"] = dict(kind="button", index=0)
    profile = ControllerProfile(IDENTITY, bindings)
    bindings["a"]["index"] = 999
    path = tmp_path / "nested" / "profile.json"
    profile.save(path)
    restored = ControllerProfile.load(path)
    joystick = Mock()
    joystick.get_button.side_effect = lambda i: i == 0
    assert restored.read(joystick).pressed == frozenset({"a"})
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize(
    "direction,hat",
    [("up", (1, 1)), ("down", (-1, -1)), ("left", (-1, 1)), ("right", (1, -1))],
)
def test_hat_direction_includes_diagonal(direction, hat):
    bindings = dict.fromkeys(CONTROLS)
    bindings[f"dpad_{direction}"] = dict(kind="hat", index=0, direction=direction)
    joystick = Mock()
    joystick.get_hat.return_value = hat
    assert (
        f"dpad_{direction}"
        in ControllerProfile(IDENTITY, bindings).read(joystick).pressed
    )


def test_calibration_reversed_y_and_nonstandard_trigger_range():
    bindings = dict.fromkeys(CONTROLS)
    bindings["left_y"] = dict(kind="axis", index=1, rest=0.05, end=-1.0, opposite=1.0)
    bindings["trigger_left"] = dict(kind="axis", index=4, rest=1.0, end=-1.0)
    joystick = Mock()
    joystick.get_axis.side_effect = lambda i: -1.0
    state = ControllerProfile(IDENTITY, bindings).read(joystick)
    assert state.left_y == 1 and state.trigger_left == 1


@pytest.mark.parametrize(
    "binding",
    [
        {"kind": "button", "index": -1},
        {"kind": "button", "index": True},
        {"kind": "button", "index": 999},
        {"kind": "hat", "index": 0, "direction": "diagonal"},
        {"kind": "axis", "index": 0, "rest": 0, "end": 1},
    ],
)
def test_bad_button_bindings_rejected(binding):
    bindings = dict.fromkeys(CONTROLS)
    bindings["a"] = binding
    with pytest.raises(ValueError):
        ControllerProfile(IDENTITY, bindings)


def test_failed_atomic_replace_preserves_previous_profile(tmp_path, monkeypatch):
    from padrelay.client import controller_profile

    path = tmp_path / "profile.json"
    profile = ControllerProfile(IDENTITY, dict.fromkeys(CONTROLS))
    profile.save(path)
    before = path.read_bytes()
    monkeypatch.setattr(
        controller_profile.os, "replace", Mock(side_effect=OSError("disk error"))
    )
    with pytest.raises(OSError):
        profile.save(path)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_profile_schema_version_and_unknown_fields(tmp_path):
    path = tmp_path / "profile.json"
    ControllerProfile(IDENTITY, dict.fromkeys(CONTROLS)).save(path)
    data = json.loads(path.read_text())
    data["legacy"] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        ControllerProfile.load(path)


@pytest.mark.parametrize("end,opposite", [(1.0, -0.8), (-1.0, 0.8)])
def test_stick_offset_and_asymmetric_travel_reach_both_extremes(
    tmp_path, end, opposite
):
    bindings = dict.fromkeys(CONTROLS)
    rest = 0.05
    bindings["left_y"] = dict(
        kind="axis", index=1, rest=rest, end=end, opposite=opposite
    )
    path = tmp_path / "profile.json"
    ControllerProfile(IDENTITY, bindings).save(path)
    profile = ControllerProfile.load(path)
    joystick = Mock()
    for physical, expected in (
        (rest, 0.0),
        (end, 1.0),
        (opposite, -1.0),
        ((rest + end) / 2, 0.5),
        ((rest + opposite) / 2, -0.5),
    ):
        joystick.get_axis.return_value = physical
        assert profile.read(joystick).left_y == pytest.approx(expected)


@pytest.mark.parametrize("opposite", [None, True, float("nan"), 2, 0, 0.5])
def test_invalid_or_missing_opposite_stick_endpoint_is_rejected(opposite):
    bindings = dict.fromkeys(CONTROLS)
    binding = dict(kind="axis", index=0, rest=0, end=1)
    if opposite is not None:
        binding["opposite"] = opposite
    bindings["left_x"] = binding
    with pytest.raises(ValueError):
        ControllerProfile(IDENTITY, bindings)
