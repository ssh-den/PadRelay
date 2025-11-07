Installation
============

PadRelay can be installed in multiple ways depending on your use case.

System Requirements
-------------------

Client Requirements
~~~~~~~~~~~~~~~~~~~

* Python 3.6 or higher
* pygame library
* Any operating system (Windows, Linux, macOS)
* A physical gamepad connected to your system

Server Requirements
~~~~~~~~~~~~~~~~~~~

* Python 3.6 or higher
* Windows operating system (for vgamepad support)
* `ViGEmBus driver <https://github.com/ViGEm/ViGEmBus>`_ installed
* vgamepad library

.. note::
   The server requires Windows because the vgamepad library uses ViGEmBus,
   which is Windows-only. The client can run on any platform.

Installation Methods
--------------------

Method 1: Install from PyPI (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simplest way to install PadRelay is from PyPI:

.. code-block:: bash

   pip install padrelay

This installs the base package with client dependencies. For server installation on Windows:

.. code-block:: bash

   pip install padrelay[server]

This will install both ``padrelay`` and ``vgamepad`` with all necessary dependencies.

After installation, you'll have three command-line tools available:

* ``padrelay-client`` - Run the gamepad client
* ``padrelay-server`` - Run the virtual gamepad server (Windows only)
* ``padrelay-keymapper`` - Create custom controller mappings

Method 2: Install from Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For development or to get the latest features:

.. code-block:: bash

   git clone https://github.com/ssh-den/PadRelay.git
   cd PadRelay
   pip install -e .

For server installation with vgamepad:

.. code-block:: bash

   pip install -e .[server]

Method 3: Install Dependencies Manually
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer to manage dependencies yourself:

.. code-block:: bash

   git clone https://github.com/ssh-den/PadRelay.git
   cd PadRelay
   pip install -r requirements.txt

Then install vgamepad on Windows:

.. code-block:: bash

   pip install vgamepad

Installing ViGEmBus (Windows Server Only)
-----------------------------------------

The server requires the ViGEmBus driver to create virtual gamepads on Windows.

1. Download the latest ViGEmBus installer from the `releases page <https://github.com/ViGEm/ViGEmBus/releases>`_
2. Run the installer (ViGEmBusSetup_x64.msi or ViGEmBusSetup_x86.msi depending on your system)
3. Restart your computer after installation
4. Verify installation by checking Device Manager for "Nefarius Virtual Gamepad Emulation Bus"

.. warning::
   ViGEmBus requires administrator privileges to install. Make sure to run
   the installer as administrator.

Optional Dependencies
---------------------

TLS/SSL Support
~~~~~~~~~~~~~~~

For secure connections, TLS support is included by default via the ``cryptography`` package:

.. code-block:: bash

   pip install cryptography>=41.0.0 cffi>=1.15.0

These are automatically installed with the base package.

Verifying Installation
----------------------

To verify your installation:

Client Verification
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   padrelay-client --help

You should see the help message with all available options.

Server Verification (Windows)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   padrelay-server --help

Key Mapper Verification
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   padrelay-keymapper --help

Testing Gamepad Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~

To test if your gamepad is detected:

.. code-block:: python

   import pygame
   pygame.init()
   pygame.joystick.init()
   print(f"Number of joysticks: {pygame.joystick.get_count()}")
   if pygame.joystick.get_count() > 0:
       joystick = pygame.joystick.Joystick(0)
       joystick.init()
       print(f"Joystick name: {joystick.get_name()}")
       print(f"Number of buttons: {joystick.get_numbuttons()}")

Upgrading
---------

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade padrelay

Or for server installation:

.. code-block:: bash

   pip install --upgrade padrelay[server]

Uninstallation
--------------

To uninstall PadRelay:

.. code-block:: bash

   pip uninstall padrelay

.. note::
   This does not uninstall ViGEmBus. To remove ViGEmBus, use the Windows
   "Add or Remove Programs" feature.

Troubleshooting Installation
-----------------------------

Permission Errors
~~~~~~~~~~~~~~~~~

If you get permission errors during installation:

.. code-block:: bash

   pip install --user padrelay

Or use a virtual environment:

.. code-block:: bash

   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install padrelay

vgamepad Installation Fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If vgamepad fails to install, ensure you have:

1. Windows operating system
2. Visual C++ Build Tools installed
3. Latest version of pip: ``pip install --upgrade pip``

pygame Installation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

On Linux, you may need additional dependencies:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install python3-pygame

   # Fedora
   sudo dnf install python3-pygame

   # Arch Linux
   sudo pacman -S python-pygame

On macOS:

.. code-block:: bash

   brew install pygame

Next Steps
----------

After installation, proceed to the :doc:`quickstart` guide to set up and run your first gamepad relay session.
