import io
from types import SimpleNamespace
from unittest.mock import Mock

import pygame
import pytest

from padrelay.core.console_input import ConsoleInput
from padrelay.scripts import key_mapper


@pytest.fixture
def mapper(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(
        key_mapper,
        "time",
        SimpleNamespace(
            monotonic=lambda: clock[0],
            sleep=lambda value: clock.__setitem__(0, clock[0] + value),
        ),
    )
    monkeypatch.setattr(pygame.event, "get", lambda: [])
    instance = key_mapper.ControllerMapper("unused.json")
    instance.joystick = Mock()
    instance.joystick.get_numaxes.return_value = 1
    instance.joystick.get_numhats.return_value = 0
    return instance, clock


@pytest.mark.parametrize("move_at", [2.9, 3.1])
def test_axis_movement_during_and_after_countdown(mapper, move_at):
    instance, clock = mapper
    instance.joystick.get_axis.side_effect = lambda i: float(clock[0] >= move_at)
    assert instance.capture_axis(timeout=0.5) == dict(
        kind="axis", index=0, rest=0.0, end=1.0
    )


def test_peak_and_negative_direction_calibration(mapper):
    instance, clock = mapper
    instance.joystick.get_axis.side_effect = lambda i: (
        0.0 if clock[0] < 3 else (-0.4 if clock[0] < 3.2 else -1.0)
    )
    assert instance.capture_axis(timeout=0.5)["end"] == -1.0


def test_button_held_at_start_then_repressed(mapper):
    instance, _ = mapper
    instance.joystick.get_numbuttons.return_value = 1
    instance.joystick.get_button.side_effect = [True, True, False, True]
    assert instance.capture_button(timeout=1) == dict(kind="button", index=0)


@pytest.mark.parametrize(
    "direction,hat",
    [("up", (0, 1)), ("down", (0, -1)), ("left", (-1, 0)), ("right", (1, 0))],
)
def test_each_hat_direction_is_captured(mapper, direction, hat):
    instance, _ = mapper
    instance.joystick.get_numbuttons.return_value = 0
    instance.joystick.get_numhats.return_value = 1
    instance.joystick.get_hat.return_value = hat
    assert instance.capture_button(timeout=1) == dict(
        kind="hat", index=0, direction=direction
    )


def test_terminal_reader_preserves_enter_and_eof():
    console = ConsoleInput(io.StringIO("\nr\n"))
    console._thread.join(timeout=1)
    assert console.pop() == ""
    assert console.pop() == "r"
    with pytest.raises(EOFError):
        console.pop()
    console.close()


def test_mapper_opens_selected_index(mapper, monkeypatch):
    instance, _ = mapper
    instance.joystick_index = 1
    factory = Mock(return_value=instance.joystick)
    monkeypatch.setattr(pygame.joystick, "Joystick", factory)
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 2)
    assert instance.detect_controller()
    factory.assert_called_once_with(1)


@pytest.mark.parametrize(
    "instance_id,hat,expected",
    [
        (7, (0, 1), dict(kind="hat", index=0, direction="up")),
        (8, (0, 1), None),
        (7, (1, 1), None),
    ],
)
def test_short_hat_events_respect_device_and_cardinal_direction(
    mapper, monkeypatch, instance_id, hat, expected
):
    instance, _ = mapper
    instance.joystick.get_instance_id.return_value = 7
    instance.joystick.get_numbuttons.return_value = 0
    instance.joystick.get_numhats.return_value = 1
    instance.joystick.get_hat.return_value = (0, 0)
    batches = [
        [
            SimpleNamespace(
                type=pygame.JOYHATMOTION, instance_id=instance_id, hat=0, value=hat
            ),
            SimpleNamespace(
                type=pygame.JOYHATMOTION, instance_id=instance_id, hat=0, value=(0, 0)
            ),
        ]
    ]
    monkeypatch.setattr(pygame.event, "get", lambda: batches.pop(0) if batches else [])
    assert instance.capture_button(timeout=0.05) == expected


@pytest.mark.parametrize("opposite", [0.8, 0.05])
def test_stick_capture_calibrates_both_ends_of_same_axis(mapper, monkeypatch, opposite):
    instance, clock = mapper
    phase = [False]
    instance.joystick.get_numaxes.return_value = 2
    instance.joystick.get_axis.side_effect = lambda i: (
        (opposite if i == 0 else -1.0)
        if phase[0]
        else (0.05 if clock[0] < 3 else -0.9) if i == 0 else 0.0
    )
    monkeypatch.setattr(instance, "_prompt", lambda text: phase.__setitem__(0, True))
    binding = instance.capture_axis(timeout=0.1, bidirectional=True)
    if opposite == 0.05:
        assert binding is None
    else:
        assert binding == dict(kind="axis", index=0, rest=0.05, end=-0.9, opposite=0.8)


def test_closed_terminal_cancels_neutral_wait_even_with_held_button(
    mapper, monkeypatch
):
    instance, _ = mapper
    monkeypatch.setattr(instance, "_prompt", lambda text: "")
    instance.joystick.get_numbuttons.return_value = 1
    instance.joystick.get_button.return_value = True
    instance.console = Mock()
    instance.console.pop.side_effect = EOFError("Terminal closed")
    with pytest.raises(EOFError):
        instance._neutral()
