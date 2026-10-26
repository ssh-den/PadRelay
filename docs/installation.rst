Installation
============

Use Python **3.11 or newer** in a virtual environment. The client runs where
Python and pygame support the attached controller, including Windows, Linux
and macOS. This documentation's server setup targets Windows with vgamepad and
the ViGEmBus driver.

Install the Package
-------------------

For the client and key mapper:

.. code-block:: bash

   python -m pip install padrelay

For the Windows server:

.. code-block:: bash

   python -m pip install "padrelay[server]"

The base package installs pygame and cryptography. The server extra adds
vgamepad; install ViGEmBus using its
`project release instructions <https://github.com/ViGEm/ViGEmBus/releases>`_.
Driver installation is separate from the Python package and may require a
restart. Verify the virtual device through ``joy.cpl`` when running the server.

For a repository checkout, use ``python -m pip install -e .`` or
``python -m pip install -e ".[server]"``. Contributor tools are installed with
the ``dev`` extra; see :doc:`development`. Installing only ``requirements.txt``
does not register PadRelay's package and CLI entry points.

Check the Environment
---------------------

.. code-block:: bash

   python --version
   python -m pip show padrelay
   padrelay-client --help
   padrelay-server --help
   padrelay-keymapper --help

There is no CLI ``--version`` flag; use package metadata to check the installed
version. If a command is missing, activate the environment in which you
installed it. The module entry points also work, for example
``python -m padrelay.scripts.client --help``.

Use :doc:`quickstart` to configure credentials, certificate trust and the
listener. TCP needs its TCP port allowed; UDP v2 needs both TCP and UDP on the
same port. These network changes require compatible client and server builds;
the current repository is not necessarily the same code as a published package.

Upgrade
-------

.. code-block:: bash

   python -m pip install --upgrade padrelay

Use ``"padrelay[server]"`` on the server, or update and reinstall your checkout.
When moving from legacy UDP, upgrade both endpoints and configure verified TLS
control as described in :doc:`user_guide/tls_setup`.

For missing pygame, vgamepad or driver errors, see
:doc:`user_guide/troubleshooting`. Removing the Python package does not remove
the Windows driver, saved configuration or identities under ``~/.padrelay``.
