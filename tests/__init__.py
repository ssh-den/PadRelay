import sys
import types

# Provide a minimal pygame stub to satisfy imports during tests
if "pygame" not in sys.modules:
    joystick = types.SimpleNamespace(
        init=lambda: None,
        Joystick=lambda idx: types.SimpleNamespace(
            init=lambda: None,
            get_name=lambda: "dummy",
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
        event=types.SimpleNamespace(pump=lambda: None, get=lambda: []),
        error=RuntimeError,
        JOYDEVICEREMOVED=1542,
        JOYBUTTONDOWN=1539,
        JOYHATMOTION=1538,
    )
    for index, name in enumerate(
        ("LEFTX", "LEFTY", "RIGHTX", "RIGHTY", "TRIGGERLEFT", "TRIGGERRIGHT")
    ):
        setattr(pygame_stub, f"CONTROLLER_AXIS_{name}", index)
    for index, name in enumerate(
        (
            "A",
            "B",
            "X",
            "Y",
            "BACK",
            "GUIDE",
            "START",
            "LEFTSTICK",
            "RIGHTSTICK",
            "LEFTSHOULDER",
            "RIGHTSHOULDER",
            "DPAD_UP",
            "DPAD_DOWN",
            "DPAD_LEFT",
            "DPAD_RIGHT",
        )
    ):
        setattr(pygame_stub, f"CONTROLLER_BUTTON_{name}", index)
    controller = types.SimpleNamespace(
        init=lambda: None, is_controller=lambda i: False, Controller=None
    )
    sys.modules["pygame._sdl2"] = types.SimpleNamespace(controller=controller)
    sys.modules["pygame"] = pygame_stub
