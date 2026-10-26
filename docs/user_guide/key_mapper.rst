Controller Profiles
===================

Recognized SDL GameControllers work automatically. To calibrate one or map an
unknown physical device, run this on the client machine:

.. code-block:: bash

   padrelay-keymapper --joystick-index 0 --output controller_profile.json
   padrelay-client --controller-profile controller_profile.json

Select the same physical device with ``--joystick-index`` in both commands.
The mapper supports ``--polling-interval`` in (0, 0.1] seconds, default 0.01.
It has terminal input on Windows, Linux and macOS; no pygame window focus is
required. Return controls to neutral, press Enter, and follow each prompt.
Enter during capture stops that attempt; ``r`` retries; ``s`` explicitly leaves
the control unmapped. Every D-pad direction is captured independently, including
hat controls. A diagonal is not accepted as a cardinal calibration direction.

Axis neutral is sampled before the countdown. Move to full travel and hold;
the mapper records the largest change, its sign and the resting value. For
sticks it then asks for the opposite direction on the same axis. Each side is
normalized against its own endpoint, preserving full travel with an offset
center or asymmetric range. Triggers need only their released and fully pressed
positions. This supports reversed axes and triggers resting at -1, 0 or +1.
After capture, test the normalized controls in the preview before confirming the save. Ctrl+C or
closed terminal input cancels without replacing an existing profile.

Profile Ownership and Validation
--------------------------------

Profiles are versioned JSON files owned by the client. They bind physical
buttons/hats/axes to logical controls, and include the GUID, name, platform and
input counts of the device. Calibration thresholds are stored in this file:
``dead_zone`` defaults to 0.1; ``trigger_threshold`` defaults to 0.05.
The file is validated on load and saved through an atomic replacement.
Axis bindings store ``rest`` and ``end``; stick bindings additionally require
``opposite``. Stick endpoints must lie on opposite sides of neutral, each at
least 0.3 raw units away. Regenerate preliminary profiles missing ``opposite``;
the client does not guess an unmeasured endpoint.

The profile must explicitly bind or skip every logical control. A skipped
control is neutral, not a fallback to a guessed index. Physical indices must
fit the recorded device. The client refuses a mismatched identity or malformed
profile. GUIDs identify a model/mode rather than a unique unit: ambiguous
reconnection among identical devices requires explicit selection and restart.

Set ``[joystick] profile = controller_profile.json`` in the client INI as an
alternative to the CLI flag. Paths are relative to the working directory.

Migration and Output
--------------------

Protocol 2.0 does not accept the old physical arrays or server INI maps.
Regenerate the profile on the client rather than copying old mapping sections.
Remove ``[button_mapping_*]``, ``[axis_mapping]`` and ``[axis_options]`` from the
server INI; they now cause an explicit startup error. Keep network, credentials,
TLS and ``[vgamepad]`` settings in their respective INI files.

The server receives only logical input. Its output adapter supports Xbox buttons
and DS4 ordinary buttons, D-pad diagonals/neutral, and Guide mapped to PS through
the native special-button API. Stick Y is positive-up in the protocol and
converted for the target. Touchpad, gyro and feedback forwarding are not part
of this controller-state contract.

Check the final virtual output in Windows ``joy.cpl``. Include the physical
model, OS and driver mode when sharing a profile; never include credentials.
