"""Capture a device-bound client profile using terminal prompts and raw inputs."""

import argparse
import math
import time
from pathlib import Path
from typing import Any

import pygame

from ..client.controller_profile import (
    CONTROLS,
    HAT_DIRECTIONS,
    ControllerProfile,
    DeviceIdentity,
)
from ..core.console_input import ConsoleInput
from ..core.controller_state import AXES, BUTTONS

INSTRUCTIONS = {
    "a": "A / bottom face button",
    "b": "B / right face button",
    "x": "X / left face button",
    "y": "Y / top face button",
    "lb": "left bumper",
    "rb": "right bumper",
    "view": "View / Share",
    "menu": "Menu / Options",
    "guide": "Xbox / PS",
    "left_stick": "left stick click",
    "right_stick": "right stick click",
    "dpad_up": "D-pad up",
    "dpad_down": "D-pad down",
    "dpad_left": "D-pad left",
    "dpad_right": "D-pad right",
    "left_x": "left stick fully RIGHT",
    "left_y": "left stick fully UP",
    "right_x": "right stick fully RIGHT",
    "right_y": "right stick fully UP",
    "trigger_left": "left trigger fully",
    "trigger_right": "right trigger fully",
}


class ControllerMapper:
    def __init__(
        self, output_path: str, polling_interval: float = 0.01, joystick_index: int = 0
    ):
        if (
            joystick_index < 0
            or not math.isfinite(polling_interval)
            or not 0 < polling_interval <= 0.1
        ):
            raise ValueError("Use a nonnegative index and polling interval in (0, 0.1]")
        self.output_path = Path(output_path)
        self.polling_interval = polling_interval
        self.joystick_index = joystick_index
        self.joystick: Any = None
        self.console: ConsoleInput | None = None
        self.bindings: dict[str, dict | None] = {name: None for name in CONTROLS}

    def detect_controller(self) -> bool:
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() <= self.joystick_index:
            print("Controller not found; connect it and check --joystick-index")
            return False
        self.joystick = pygame.joystick.Joystick(self.joystick_index)
        self.joystick.init()
        print(f"Selected {self.joystick_index}: {self.joystick.get_name()}")
        return True

    def _events(self) -> list:
        events = pygame.event.get()
        for event in events:
            if (
                event.type == pygame.JOYDEVICEREMOVED
                and event.instance_id == self.joystick.get_instance_id()
            ):
                raise RuntimeError(
                    "Selected controller disconnected; reconnect and restart mapping"
                )
        return events

    def check_for_skip(self) -> bool:
        return self.console is not None and self.console.pop() is not None

    def _prompt(self, text: str) -> str:
        assert self.console is not None
        print(text, flush=True)
        while True:
            self._events()
            line = self.console.pop()
            if line is not None:
                return line.strip().lower()
            time.sleep(self.polling_interval)

    def _neutral(self) -> None:
        self._prompt("Release ALL controls and center sticks. Press Enter when ready.")
        # Buttons and hats have an observable neutral; arbitrary axes need the
        # user's neutral position because their rest may be -1, 0 or +1.
        while True:
            self._events()
            self.check_for_skip()
            if not any(
                self.joystick.get_button(i)
                for i in range(self.joystick.get_numbuttons())
            ) and not any(
                any(self.joystick.get_hat(i))
                for i in range(self.joystick.get_numhats())
            ):
                return
            time.sleep(self.polling_interval)

    @staticmethod
    def _hat_binding(index: int, hat: tuple) -> dict | None:
        directions = [
            name
            for name, (coordinate, value) in HAT_DIRECTIONS.items()
            if hat[coordinate] == value
        ]
        if len(directions) == 1:
            return {"kind": "hat", "index": index, "direction": directions[0]}
        return None

    def capture_button(self, timeout: float = 20) -> dict | None:
        previous = [
            self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())
        ]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            events = self._events()
            if self.check_for_skip():
                return None
            for event in events:
                if (
                    getattr(event, "instance_id", None)
                    != self.joystick.get_instance_id()
                ):
                    continue
                if event.type == pygame.JOYBUTTONDOWN:
                    return {"kind": "button", "index": event.button}
                if event.type == pygame.JOYHATMOTION:
                    binding = self._hat_binding(event.hat, event.value)
                    if binding is not None:
                        return binding
            for index, old in enumerate(previous):
                value = self.joystick.get_button(index)
                if value and not old:
                    return {"kind": "button", "index": index}
                previous[index] = value
            for index in range(self.joystick.get_numhats()):
                binding = self._hat_binding(index, self.joystick.get_hat(index))
                if binding is not None:
                    return binding
            time.sleep(self.polling_interval)
        return None

    def capture_axis(
        self, timeout: float = 5, *, bidirectional: bool = False
    ) -> dict | None:
        self._events()
        baseline = [
            self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())
        ]
        print(
            "Starting in 3 seconds; hold the requested direction at full travel.",
            flush=True,
        )
        for _ in range(3):
            self._events()
            time.sleep(1)
        print("GO (Enter skips)", flush=True)
        best: dict[str, Any] | None = None
        largest_change = 0.3
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._events()
            if self.check_for_skip():
                return None
            for index, rest in enumerate(baseline):
                value = self.joystick.get_axis(index)
                delta = abs(value - rest)
                if delta > largest_change:
                    largest_change = delta
                    best = {"kind": "axis", "index": index, "rest": rest, "end": value}
            time.sleep(self.polling_interval)
        if best is not None and bidirectional:
            self._prompt(
                "Next calibrate the SAME stick axis in the OPPOSITE direction. "
                "Press Enter when ready."
            )
            print(
                "Move fully in the opposite direction and hold (Enter skips).",
                flush=True,
            )
            opposite = best["rest"]
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                self._events()
                if self.check_for_skip():
                    return None
                value = self.joystick.get_axis(best["index"])
                if (value - opposite) * (best["end"] - best["rest"]) < 0:
                    opposite = value
                time.sleep(self.polling_interval)
            if abs(opposite - best["rest"]) < 0.3:
                return None
            best["opposite"] = opposite
        return best

    def generate_config(self) -> None:
        if self.joystick is None:
            raise ValueError("No selected controller")
        ControllerProfile(DeviceIdentity.read(self.joystick), self.bindings).save(
            self.output_path
        )
        print(f"Profile saved: {self.output_path}")
        print(
            f"Use on the CLIENT: padrelay-client --controller-profile {self.output_path}"
        )

    def verify_mapping(self) -> None:
        assert self.console is not None
        profile = ControllerProfile(DeviceIdentity.read(self.joystick), self.bindings)
        print(
            "Test your controls now. Enter confirms; Ctrl+C cancels without saving.",
            flush=True,
        )
        previous = None
        while True:
            self._events()
            if self.console.pop() is not None:
                return
            state = profile.read(self.joystick)
            if state != previous:
                print(
                    f"Pressed: {', '.join(sorted(state.pressed)) or 'none'} | "
                    f"L({state.left_x:.2f}, {state.left_y:.2f}) "
                    f"R({state.right_x:.2f}, {state.right_y:.2f}) | "
                    f"LT {state.trigger_left:.2f}, RT {state.trigger_right:.2f}",
                    flush=True,
                )
                previous = state
            time.sleep(self.polling_interval)

    def run(self) -> None:
        try:
            if not self.detect_controller():
                return
            self.console = ConsoleInput()
            for name in CONTROLS:
                while True:
                    print(f"\nMap {name}: {INSTRUCTIONS[name]}", flush=True)
                    self._neutral()
                    if name in BUTTONS:
                        print(
                            f"Now press {INSTRUCTIONS[name]}. Enter skips.", flush=True
                        )
                        binding = self.capture_button()
                    else:
                        binding = self.capture_axis(bidirectional=name in AXES)
                    print(f"Detected: {binding}", flush=True)
                    choice = self._prompt(
                        "Enter accepts; r retries; s explicitly leaves unmapped."
                    )
                    if choice == "r" or (binding is None and choice != "s"):
                        continue
                    if choice not in ("", "s"):
                        continue
                    self.bindings[name] = binding if choice != "s" else None
                    break
            self.verify_mapping()
            if (
                self.output_path.exists()
                and self._prompt("Profile exists. Type overwrite to replace it:")
                != "overwrite"
            ):
                return
            self.generate_config()
        except (KeyboardInterrupt, EOFError):
            print("Mapping cancelled; existing profile was not changed.")
        finally:
            if self.console is not None:
                self.console.close()
            pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="controller_profile.json")
    parser.add_argument("--joystick-index", type=int, default=0)
    parser.add_argument("--polling-interval", type=float, default=0.01)
    args = parser.parse_args()
    mapper = ControllerMapper(args.output, args.polling_interval, args.joystick_index)
    mapper.run()


if __name__ == "__main__":
    main()
