Controller Mapping
==================

Run the mapper on the machine with the physical controller:

.. code-block:: bash

   padrelay-keymapper --output controller.ini

It opens the first pygame controller, asks for the virtual gamepad type, records
buttons and axes, then offers a review before saving. Follow the movement
prompts and return controls to neutral between captures. Enter-key skipping is
read through pygame events, so it may depend on the window/event focus.

The supported flags are ``--output`` (default ``controller_config.ini``) and
``--polling-interval`` (default ``0.1`` seconds). There is no mapper
``--joystick-index`` flag. Disconnect other controllers if the first detected
device is not the one you need.

Apply the Result on the Server
------------------------------

The generated INI contains ``[server]`` defaults, ``[vgamepad]``, button and axis
maps, and axis options. It is not a complete client configuration and contains
no password or certificate trust configuration. Its default server host is
``127.0.0.1``.

Copy the mapping sections into an existing server INI, or add the server's
address, credentials and transport settings to the generated file before use:

.. code-block:: bash

   padrelay-server --config controller.ini

Keep the client's network, trust and joystick settings in its own INI. The
client does not apply these mappings. The mapper writes ``trigger_threshold =
0.05``; the server fallback without that setting is ``0.1``.

Adjust a Mapping
----------------

Button keys are physical indices and values are virtual button constants.
For example, swapping the first two buttons on an Xbox target:

.. code-block:: ini

   [button_mapping_xbox360]
   0 = XUSB_GAMEPAD_B
   1 = XUSB_GAMEPAD_A

A custom button map replaces the defaults, so include the other buttons you
need. Axis maps use ``left_stick_x/y``, ``right_stick_x/y`` and
``trigger_left/right``. Stick pairs need both coordinates; trigger axes are
expected in [-1, 1]. Y inversion applies in this mapped path.

.. code-block:: ini

   [axis_options]
   dead_zone = 0.15
   trigger_threshold = 0.05
   invert_left_y = true
   invert_right_y = false

These are hard cutoffs, not response curves. Full field names, defaults and
fallback rules are in :doc:`../configuration`.

Known Limits and Verification
-----------------------------

The mapper may record D-pad hats in a ``*_hat`` section, but the server currently
does not read those sections or apply incoming hats to virtual output. A D-pad
reported as ordinary mapped buttons can work; a hat-only D-pad needs code
support, not another certificate or network setting. DS4 mode does not add
touchpad or gyro support.

Test buttons, sticks and triggers in Windows ``joy.cpl`` after copying the
mapping. When sharing it, include the controller model, driver mode, OS and
which inputs you verified; remove credentials and machine-specific paths.
