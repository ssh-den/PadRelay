import configparser

from padrelay.server.input_processor import GamepadHandler


class DummyGamepad:
    def __init__(self):
        self.calls = []

    def get_button_mapping(self):
        return {0: 10, 1: 11}

    def press_button(self, *, button):
        self.calls.append(('press', button))

    def release_button(self, *, button):
        self.calls.append(('release', button))

    def left_joystick_float(self, **kw):
        self.calls.append(('left', kw))

    def right_joystick_float(self, **kw):
        self.calls.append(('right', kw))

    def left_trigger_float(self, **kw):
        self.calls.append(('lt', kw))

    def right_trigger_float(self, **kw):
        self.calls.append(('rt', kw))

    def update(self):
        self.calls.append(('update', None))


def test_basic_axis_processing():
    gamepad = DummyGamepad()
    handler = GamepadHandler(gamepad)
    message = {
        'buttons': [True, False],
        'axes': [0.5, -0.5, 0.2, -0.2],
        'triggers': [0.5, 0.7],
    }
    handler.process(message)

    assert ('press', 10) in gamepad.calls
    assert ('release', 11) in gamepad.calls
    assert ('left', {'x_value_float': 0.5, 'y_value_float': -0.5}) in gamepad.calls
    assert ('right', {'x_value_float': 0.2, 'y_value_float': -0.2}) in gamepad.calls
    assert ('lt', {'value_float': 0.5}) in gamepad.calls
    assert ('rt', {'value_float': 0.7}) in gamepad.calls
    assert ('update', None) == gamepad.calls[-1]


def test_advanced_axis_mapping_with_inversion():
    cfg = configparser.ConfigParser()
    cfg.add_section('axis_options')
    cfg['axis_options']['dead_zone'] = '0.1'
    cfg['axis_options']['invert_left_y'] = 'true'
    cfg['axis_options']['invert_right_y'] = 'true'
    cfg['axis_options']['trigger_threshold'] = '0.2'
    cfg.add_section('axis_mapping')
    cfg['axis_mapping'] = {
        'left_stick_x': '0',
        'left_stick_y': '1',
        'right_stick_x': '2',
        'right_stick_y': '3',
        'trigger_left': '4',
        'trigger_right': '5',
    }
    gamepad = DummyGamepad()
    handler = GamepadHandler(gamepad, cfg)
    message = {
        'axes': [0.9, -0.5, 0.5, -0.5, -1.0, 1.0],
    }
    handler.process(message)

    assert ('left', {'x_value_float': 0.9, 'y_value_float': 0.5}) in gamepad.calls
    assert ('right', {'x_value_float': 0.5, 'y_value_float': 0.5}) in gamepad.calls
    assert ('lt', {'value_float': 0.0}) in gamepad.calls
    assert ('rt', {'value_float': 1.0}) in gamepad.calls
