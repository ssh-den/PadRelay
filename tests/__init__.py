import sys
import types

# Provide a minimal pygame stub to satisfy imports during tests
if 'pygame' not in sys.modules:
    joystick = types.SimpleNamespace(
        init=lambda: None,
        Joystick=lambda idx: types.SimpleNamespace(
            init=lambda: None,
            get_name=lambda: 'dummy',
            get_numaxes=lambda: 0,
            get_numbuttons=lambda: 0,
            get_numhats=lambda: 0,
            get_button=lambda i: 0,
            get_axis=lambda i: 0.0,
            get_hat=lambda i: (0, 0),
        ),
        get_count=lambda: 0,
    )
    pygame_stub = types.SimpleNamespace(
        init=lambda: None,
        quit=lambda: None,
        joystick=joystick,
        event=types.SimpleNamespace(pump=lambda: None),
    )
    sys.modules['pygame'] = pygame_stub
