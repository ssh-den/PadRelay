# Controller Profiles

See [the maintained guide](docs/user_guide/key_mapper.rst).

Run on the physical-controller machine:

```sh
padrelay-keymapper --joystick-index 0 --output controller_profile.json
padrelay-client --joystick-index 0 --controller-profile controller_profile.json
```

The mapper uses terminal prompts, supports buttons and hats, calibrates axes,
and previews the same normalized state used by the client. Profiles are
device-bound JSON files saved atomically. They belong on the client.

Protocol 2.0 carries one logical snapshot. Old server INI mapping/calibration
sections are rejected; regenerate a client profile and remove those sections.
Update both peers together.
