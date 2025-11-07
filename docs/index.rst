PadRelay Documentation
======================

.. image:: https://img.shields.io/pypi/v/padrelay.svg
   :target: https://pypi.org/project/padrelay/
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/padrelay.svg
   :target: https://pypi.org/project/padrelay/
   :alt: Python Versions

.. image:: https://img.shields.io/github/license/ssh-den/PadRelay.svg
   :target: https://github.com/ssh-den/PadRelay/blob/main/LICENSE
   :alt: License

**PadRelay** is a client-server application that forwards gamepad input from a local machine to a Windows PC where a virtual controller is created. The client captures input with pygame and the server emulates either an Xbox 360 or DualShock 4 gamepad using the vgamepad library.

Key Features
------------

* **Cross-Platform Client**: Works with Python 3.6+ on any system with pygame
* **Windows Server**: Uses ViGEmBus to create virtual Xbox 360 or DualShock 4 gamepads
* **Flexible Transport**: Choose between TCP (reliable) or UDP (low latency)
* **Secure Authentication**: Challenge/response for TCP and token authentication for UDP
* **TLS/SSL Support**: Optional encryption for TCP connections
* **Rate Limiting**: Protects servers from excessive requests
* **Automatic Reconnection**: Client automatically reconnects if server disconnects
* **Controller Mapping**: Built-in key mapper utility for custom controller layouts
* **Comprehensive Logging**: Detailed debug logging with log sanitization

Use Cases
---------

* Stream gamepad input from Linux/Mac to Windows gaming PC
* Remote gaming over local network or VPN
* Use non-standard controllers with games expecting Xbox/PS4 controllers
* Share a single physical controller with multiple machines

Quick Links
-----------

* `GitHub Repository <https://github.com/ssh-den/PadRelay>`_
* `PyPI Package <https://pypi.org/project/padrelay/>`_
* `Issue Tracker <https://github.com/ssh-den/PadRelay/issues>`_

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart
   configuration

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/client
   user_guide/server
   user_guide/key_mapper
   user_guide/tls_setup
   user_guide/troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Technical Documentation

   architecture
   security
   protocol
   api

.. toctree::
   :maxdepth: 2
   :caption: Development

   development
   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
