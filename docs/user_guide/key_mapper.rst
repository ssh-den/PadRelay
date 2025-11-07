Key Mapper Guide
================

The PadRelay key mapper helps you create custom controller mappings for non-standard gamepads.

Overview
--------

The key mapper utility (``padrelay-keymapper``) walks you through recording your physical controller's buttons and axes, then generates a configuration file with the correct mappings.

When to Use
-----------

Use the key mapper when:

* Default mappings don't match your controller
* Using a third-party or uncommon controller
* Buttons are mapped incorrectly
* You want to customize button layout
* Creating a reusable configuration for a specific controller

Running the Key Mapper
-----------------------

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   padrelay-keymapper --output my_controller.ini

The tool will:

1. Detect your connected controller
2. Ask which virtual gamepad type to emulate (Xbox 360 or DS4)
3. Prompt you to press each button
4. Prompt you to move each axis
5. Save the configuration to the output file

Interactive Session
~~~~~~~~~~~~~~~~~~~

Example session:

.. code-block:: text

   PadRelay Controller Mapper
   ==========================

   Detected controller: Logitech Gamepad F310

   Select virtual gamepad type:
   1. Xbox 360
   2. DualShock 4
   Choice: 1

   --- Mapping Buttons ---

   Press button for A (or Enter to skip): [Press button 0]
   Detected button 0

   Press button for B (or Enter to skip): [Press button 1]
   Detected button 1

   Press button for X (or Enter to skip): [Press button 2]
   Detected button 2

   ...

   --- Mapping Axes ---

   Move LEFT STICK horizontally:
   Detected axis 0

   Move LEFT STICK vertically:
   Detected axis 1

   ...

   Configuration saved to my_controller.ini

Options
~~~~~~~

.. code-block:: text

   padrelay-keymapper [OPTIONS]

   Options:
     --output PATH     Output configuration file path (required)
     --joystick-index INTEGER    Which controller to use (default: 0)
     --help           Show help message

Mapping Process
---------------

Button Mapping
~~~~~~~~~~~~~~

For each virtual button, you'll be prompted to press the corresponding physical button:

**Xbox 360 buttons:**

* A, B, X, Y
* Left Shoulder (LB), Right Shoulder (RB)
* Back, Start
* Left Stick Press, Right Stick Press
* D-Pad Up, Down, Left, Right

**DualShock 4 buttons:**

* Cross, Circle, Square, Triangle
* L1, R1, L2, R2 (as buttons)
* Share, Options
* L3, R3
* D-Pad Up, Down, Left, Right

Axis Mapping
~~~~~~~~~~~~

For each virtual axis, you'll be prompted to move the corresponding physical control:

**Common axes:**

* Left Stick X (horizontal)
* Left Stick Y (vertical)
* Right Stick X (horizontal)
* Right Stick Y (vertical)
* Left Trigger
* Right Trigger

Skipping Mappings
~~~~~~~~~~~~~~~~~

Press **Enter** without pressing any button to skip a mapping. You can edit the generated file later to add skipped mappings.

Using Generated Configuration
------------------------------

Server Configuration
~~~~~~~~~~~~~~~~~~~~

Use the generated file with the server:

.. code-block:: bash

   padrelay-server --config my_controller.ini

Or merge into existing server configuration by copying the relevant sections.

Client Configuration
~~~~~~~~~~~~~~~~~~~~

The client typically doesn't need controller-specific configuration, but you can use the same file:

.. code-block:: bash

   padrelay-client --config my_controller.ini

Configuration File Format
-------------------------

The key mapper generates an INI file with button and axis mappings:

Example Output
~~~~~~~~~~~~~~

.. code-block:: ini

   [vgamepad]
   type = xbox360

   [button_mapping_xbox360]
   0 = XUSB_GAMEPAD_A
   1 = XUSB_GAMEPAD_B
   2 = XUSB_GAMEPAD_X
   3 = XUSB_GAMEPAD_Y
   4 = XUSB_GAMEPAD_LEFT_SHOULDER
   5 = XUSB_GAMEPAD_RIGHT_SHOULDER
   6 = XUSB_GAMEPAD_BACK
   7 = XUSB_GAMEPAD_START
   8 = XUSB_GAMEPAD_LEFT_THUMB
   9 = XUSB_GAMEPAD_RIGHT_THUMB

   [axis_mapping]
   left_stick_x = 0
   left_stick_y = 1
   right_stick_x = 2
   right_stick_y = 3
   trigger_left = 4
   trigger_right = 5

   [axis_options]
   dead_zone = 0.1
   trigger_threshold = 0.1
   invert_left_y = false
   invert_right_y = false

Manual Editing
--------------

You can manually edit the generated configuration:

Swapping Buttons
~~~~~~~~~~~~~~~~

To swap A and B buttons:

.. code-block:: ini

   [button_mapping_xbox360]
   0 = XUSB_GAMEPAD_B
   1 = XUSB_GAMEPAD_A

Inverting Axes
~~~~~~~~~~~~~~

To invert the Y axis (common for flight simulators):

.. code-block:: ini

   [axis_options]
   invert_left_y = true

Adjusting Dead Zones
~~~~~~~~~~~~~~~~~~~~~

To reduce stick drift:

.. code-block:: ini

   [axis_options]
   dead_zone = 0.15  # Increase from default 0.1

Common Controller Mappings
--------------------------

The key mapper works with many controllers:

* Xbox 360/One controllers
* PlayStation 3/4/5 controllers
* Logitech gamepads
* Generic USB controllers
* Nintendo Switch Pro Controller
* Steam Controller

Troubleshooting
---------------

Controller Not Detected
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ERROR: No controller detected

**Solutions:**

1. Connect your controller
2. Wait a few seconds for driver installation
3. Test controller in another application
4. Try a different USB port
5. Use ``--joystick-index`` if multiple controllers connected

Incorrect Button Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~

If the wrong button is detected:

1. Try again more carefully
2. Make sure only pressing one button at a time
3. Skip the mapping and edit the configuration file manually

D-Pad Not Working
~~~~~~~~~~~~~~~~~

Some controllers use axes for the D-pad instead of a hat. You'll need to manually configure this by editing the generated file.

Axis Values Inverted
~~~~~~~~~~~~~~~~~~~~

If an axis is inverted (e.g., pushing up makes the stick go down):

.. code-block:: ini

   [axis_options]
   invert_left_y = true
   invert_right_y = true

Sharing Configurations
----------------------

Configuration files are portable and can be shared:

1. Create mapping on one machine
2. Copy the ``.ini`` file to another machine
3. Use with PadRelay on the new machine

You can also contribute popular controller mappings to the PadRelay repository via pull request.

Advanced Usage
--------------

Mapping Multiple Controllers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create separate configuration files for each controller type:

.. code-block:: bash

   padrelay-keymapper --output xbox360.ini --joystick-index 0
   padrelay-keymapper --output ps4.ini --joystick-index 1

Macro Support
~~~~~~~~~~~~~

While not built into the key mapper, you can create macros by running multiple PadRelay clients with custom input processing.

Examples
--------

Example 1: PS4 Controller
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   $ padrelay-keymapper --output ps4_mapping.ini

   Detected controller: Sony DualShock 4
   Select virtual gamepad type:
   1. Xbox 360
   2. DualShock 4
   Choice: 2

   [Continue with button and axis mapping...]

Example 2: Custom Flight Stick
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   $ padrelay-keymapper --output flight_stick.ini

   Detected controller: Logitech Extreme 3D Pro
   Select virtual gamepad type:
   1. Xbox 360
   2. DualShock 4
   Choice: 1

   [Map flight stick buttons to Xbox 360 layout...]

See Also
--------

* :doc:`../configuration` - Configuration reference
* :doc:`server` - Server guide
* :doc:`troubleshooting` - Troubleshooting guide
