import configparser
from padrelay.scripts import key_mapper as key_mapper_script
from padrelay.server.input_processor import GamepadHandler


class DummyGamepad:
    def get_button_mapping(self):
        return {}

    def press_button(self, *, button):
        pass

    def release_button(self, *, button):
        pass

    def left_joystick_float(self, **kw):
        pass

    def right_joystick_float(self, **kw):
        pass

    def left_trigger_float(self, **kw):
        pass

    def right_trigger_float(self, **kw):
        pass

    def update(self):
        pass


def test_generate_config_loads_with_handler(tmp_path):
    cfg_file = tmp_path / "cfg.ini"
    mapper = key_mapper_script.ControllerMapper(str(cfg_file))
    mapper.gamepad_type = "xbox360"
    mapper.axis_mapping = {
        "left_stick_x": 0,
        "left_stick_y": 1,
        "trigger_left": 2,
        "trigger_right": 3,
    }
    mapper.generate_config()

    cfg = configparser.ConfigParser()
    cfg.read(cfg_file)
    axis_map_section = cfg["axis_mapping"]
    assert axis_map_section["left_stick_x"] == "0"
    assert axis_map_section["left_stick_y"] == "1"
    assert axis_map_section["trigger_left"] == "2"
    assert axis_map_section["trigger_right"] == "3"

    handler = GamepadHandler(DummyGamepad(), cfg)
    assert handler.axis_map["left_stick_x"] == 0
    assert handler.axis_map["left_stick_y"] == 1
    assert handler.axis_map["trigger_left"] == 2
    assert handler.axis_map["trigger_right"] == 3
