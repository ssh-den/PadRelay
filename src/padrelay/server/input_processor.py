"""Utilities that translate input messages into virtual gamepad actions"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..core.logging_utils import get_logger

logger = get_logger(__name__)


class GamepadHandler:
    """Apply received messages to a virtual gamepad"""

    def __init__(self, gamepad: "VirtualGamepad", config: Optional[object] = None) -> None:
        self.gamepad = gamepad
        self.config = config

        # Button mapping is stored on the VirtualGamepad
        self.button_mapping = gamepad.get_button_mapping()

        # Cached configuration options
        self.dead_zone: float = 0.1
        self.trigger_threshold: float = 0.1
        self.axis_map: Dict[str, int] = {}
        self.invert_left_y: bool = False
        self.invert_right_y: bool = False

        if config and hasattr(config, "has_section"):
            if config.has_section("axis_options"):
                try:
                    self.dead_zone = float(config["axis_options"].get("dead_zone", 0.1))
                    self.trigger_threshold = float(
                        config["axis_options"].get("trigger_threshold", 0.1)
                    )
                    self.invert_left_y = (
                        config["axis_options"].get("invert_left_y", "false").lower() == "true"
                    )
                    self.invert_right_y = (
                        config["axis_options"].get("invert_right_y", "false").lower() == "true"
                    )
                except Exception:  # pragma: no cover - best effort parsing
                    pass

            if config.has_section("axis_mapping"):
                try:
                    self.axis_map = {k: int(v) for k, v in config.items("axis_mapping")}
                except Exception:  # pragma: no cover
                    self.axis_map = {}

        # State used for change detection
        self.last_buttons: List[bool] = []
        self.last_axes: List[float] = []
        self.buttons_changed = True
        self.axes_changed = True
        self.update_counter = 0

    def process(self, message: Dict) -> None:
        """Process a single input message"""
        try:
            self.update_counter += 1
            force_update = self.update_counter % 30 == 0

            buttons = message.get("buttons", [])
            if buttons != self.last_buttons or force_update:
                self.process_buttons(buttons)
                self.last_buttons = list(buttons)
                self.buttons_changed = True
            else:
                self.buttons_changed = False

            axes = message.get("axes", [])
            if axes != self.last_axes or force_update:
                self.process_axes(message)
                self.last_axes = list(axes)
                self.axes_changed = True
            else:
                self.axes_changed = False

            if self.buttons_changed or self.axes_changed or force_update:
                self.gamepad.update()
        except Exception as exc:
            logger.error(f"Error processing gamepad message: {exc}")

    def process_buttons(self, buttons: List[bool]) -> None:
        """Apply button state changes"""
        for idx, pressed in enumerate(buttons):
            if idx in self.button_mapping:
                btn_const = self.button_mapping[idx]
                if pressed:
                    self.gamepad.press_button(button=btn_const)
                else:
                    self.gamepad.release_button(button=btn_const)

    def process_axes(self, message: Dict) -> None:
        """Handle axes using the loaded configuration"""
        axes = message.get("axes", [])
        if self.axis_map:
            self.process_advanced_axes(axes, message)
        else:
            self.process_basic_axes(axes, message)

    def process_advanced_axes(self, axes: List[float], message: Dict) -> None:
        """Handle axes with advanced mapping"""
        if all(k in self.axis_map for k in ("left_stick_x", "left_stick_y")):
            lx = self.axis_map["left_stick_x"]
            ly = self.axis_map["left_stick_y"]
            if len(axes) > max(lx, ly):
                x_val = axes[lx] if abs(axes[lx]) > self.dead_zone else 0.0
                y_val = axes[ly] if abs(axes[ly]) > self.dead_zone else 0.0
                if self.invert_left_y:
                    y_val = -y_val
                self.gamepad.left_joystick_float(x_value_float=x_val, y_value_float=y_val)

        if all(k in self.axis_map for k in ("right_stick_x", "right_stick_y")):
            rx = self.axis_map["right_stick_x"]
            ry = self.axis_map["right_stick_y"]
            if len(axes) > max(rx, ry):
                x_val = axes[rx] if abs(axes[rx]) > self.dead_zone else 0.0
                y_val = axes[ry] if abs(axes[ry]) > self.dead_zone else 0.0
                if self.invert_right_y:
                    y_val = -y_val
                self.gamepad.right_joystick_float(x_value_float=x_val, y_value_float=y_val)

        if "trigger_left" in self.axis_map and len(axes) > self.axis_map["trigger_left"]:
            idx = self.axis_map["trigger_left"]
            val = (axes[idx] + 1) / 2.0
            self.gamepad.left_trigger_float(value_float=val if val > self.trigger_threshold else 0.0)

        if "trigger_right" in self.axis_map and len(axes) > self.axis_map["trigger_right"]:
            idx = self.axis_map["trigger_right"]
            val = (axes[idx] + 1) / 2.0
            self.gamepad.right_trigger_float(value_float=val if val > self.trigger_threshold else 0.0)

    def process_basic_axes(self, axes: List[float], message: Dict) -> None:
        """Handle axes with the default mapping"""
        if len(axes) >= 2:
            x_val = axes[0] if abs(axes[0]) > self.dead_zone else 0.0
            y_val = axes[1] if abs(axes[1]) > self.dead_zone else 0.0
            self.gamepad.left_joystick_float(x_value_float=x_val, y_value_float=y_val)

        if len(axes) >= 4:
            x_val = axes[2] if abs(axes[2]) > self.dead_zone else 0.0
            y_val = axes[3] if abs(axes[3]) > self.dead_zone else 0.0
            self.gamepad.right_joystick_float(x_value_float=x_val, y_value_float=y_val)

        triggers = message.get("triggers", [])
        if len(triggers) >= 2:
            left = triggers[0] if triggers[0] > self.trigger_threshold else 0.0
            right = triggers[1] if triggers[1] > self.trigger_threshold else 0.0
            self.gamepad.left_trigger_float(value_float=left)
            self.gamepad.right_trigger_float(value_float=right)

