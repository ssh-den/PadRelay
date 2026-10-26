from unittest.mock import Mock

from padrelay.client.controller_profile import ControllerProfile
from padrelay.scripts.key_mapper import ControllerMapper


def test_mapper_generates_client_profile_with_device_identity(tmp_path):
    path = tmp_path / "profile.json"
    mapper = ControllerMapper(str(path))
    mapper.joystick = Mock()
    mapper.joystick.get_guid.return_value = "guid"
    mapper.joystick.get_name.return_value = "Controller"
    mapper.joystick.get_numbuttons.return_value = 15
    mapper.joystick.get_numaxes.return_value = 6
    mapper.joystick.get_numhats.return_value = 1
    mapper.bindings["a"] = dict(kind="button", index=0)
    mapper.generate_config()
    profile = ControllerProfile.load(path)
    assert profile.identity.guid == "guid"
    assert "button_mapping" not in path.read_text()
