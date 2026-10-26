PadRelay
========

PadRelay forwards physical gamepad input to a virtual Xbox 360 or DualShock 4
device on a Windows server. The client captures state with pygame; the server
uses vgamepad and ViGEmBus. Python 3.11+ is required.

TCP uses verified TLS by default. UDP v2 combines a verified TLS control
connection with encrypted, replay-protected input datagrams. Both modes require
credentials in the CLI and admit one client per server process. Start with
:doc:`quickstart`; existing UDP installations must update both endpoints and
configure certificate trust.

These pages describe the current repository. See :doc:`CHANGELOG` for changes
that have not yet been released.

.. toctree::
   :maxdepth: 2
   :caption: Setup

   installation
   quickstart
   configuration

.. toctree::
   :maxdepth: 2
   :caption: Operation

   user_guide/client
   user_guide/server
   user_guide/key_mapper
   user_guide/tls_setup
   user_guide/troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Internals

   architecture
   security
   protocol
   api

.. toctree::
   :maxdepth: 2
   :caption: Development

   development
   contributing
   CHANGELOG

* :ref:`genindex`
* :ref:`modindex`
* `Source and issues <https://github.com/ssh-den/PadRelay>`_
