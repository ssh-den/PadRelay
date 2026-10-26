Development Guide
=================

This guide is for developers who want to contribute to PadRelay or understand its internals.

Development Setup
-----------------

Prerequisites
~~~~~~~~~~~~~

* Python 3.6+
* Git
* Virtual environment tool (venv or virtualenv)
* ViGEmBus driver (for server development on Windows)

Clone Repository
~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/ssh-den/PadRelay.git
   cd PadRelay

Create Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python -m venv venv

   # Linux/macOS
   source venv/bin/activate

   # Windows
   venv\Scripts\activate

Install Dependencies
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Install in editable mode with all dependencies
   pip install -e .

   # Install development dependencies
   pip install -r requirements.txt
   pip install pytest pytest-asyncio

Project Structure
-----------------

Directory Layout
~~~~~~~~~~~~~~~~

::

    PadRelay/
    ├── src/padrelay/          # Main source code
    │   ├── client/            # Client components
    │   │   ├── client_app.py  # Client application
    │   │   ├── input.py       # Gamepad input capture
    │   │   └── constants.py   # Client constants
    │   ├── server/            # Server components
    │   │   ├── server_app.py  # Server application
    │   │   ├── virtual_gamepad.py  # Virtual gamepad interface
    │   │   ├── input_processor.py  # Input processing
    │   │   └── constants.py   # Server constants
    │   ├── protocol/          # Protocol implementation
    │   │   ├── tcp.py         # TCP protocol
    │   │   ├── udp.py         # UDP protocol
    │   │   ├── messages.py    # Message types
    │   │   └── constants.py   # Protocol constants
    │   ├── security/          # Security components
    │   │   ├── auth.py        # Authentication
    │   │   ├── rate_limiting.py  # Rate limiting
    │   │   ├── tls_utils.py   # TLS utilities
    │   │   └── password_strength.py  # Password validation
    │   ├── core/              # Core utilities
    │   │   ├── config.py      # Configuration handling
    │   │   ├── exceptions.py  # Custom exceptions
    │   │   └── logging_utils.py  # Logging setup
    │   └── scripts/           # Entry points
    │       ├── server.py      # Server entry point
    │       ├── client.py      # Client entry point
    │       └── key_mapper.py  # Key mapper utility
    ├── tests/                 # Test suite
    ├── config/                # Example configurations
    ├── docs/                  # Documentation
    ├── pyproject.toml         # Project metadata
    └── README.md              # Project README

Code Organization
~~~~~~~~~~~~~~~~~

* **Client:** Gamepad input capture and network transmission
* **Server:** Network reception and virtual gamepad output
* **Protocol:** Message serialization and transport
* **Security:** Authentication, encryption, rate limiting
* **Core:** Configuration, logging, exceptions
* **Scripts:** CLI entry points

Running Tests
-------------

Run All Tests
~~~~~~~~~~~~~

.. code-block:: bash

   pytest

Run Specific Test File
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pytest tests/test_auth.py

Run with Coverage
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pytest --cov=padrelay --cov-report=html

View coverage report at ``htmlcov/index.html``.

Run Specific Test
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pytest tests/test_auth.py::test_hash_password

Test Organization
~~~~~~~~~~~~~~~~~

Tests are organized by component:

* ``test_auth.py`` - Authentication tests
* ``test_tcp_protocol.py`` - TCP protocol tests
* ``test_udp_protocol.py`` - UDP protocol tests
* ``test_rate_limiting.py`` - Rate limiting tests
* ``test_tls_utils.py`` - TLS utility tests
* ``test_messages.py`` - Message serialization tests
* ``test_integration.py`` - End-to-end integration tests

Coding Standards
----------------

Style Guide
~~~~~~~~~~~

PadRelay follows PEP 8 with some exceptions:

* Line length: 100 characters (not 79)
* Use double quotes for strings
* Use f-strings for formatting

Type Hints
~~~~~~~~~~

Use type hints for function signatures:

.. code-block:: python

   def authenticate(self, password: str, challenge: bytes) -> bool:
       """Verify authentication challenge response."""
       # Implementation

Docstrings
~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def compute_response(self, challenge: str) -> str:
       """Compute HMAC response for authentication challenge.

       Args:
           challenge: Hex-encoded random bytes from server

       Returns:
           Hex-encoded HMAC-SHA256 response

       Raises:
           ValueError: If challenge is invalid
       """
       # Implementation

Code Formatting
~~~~~~~~~~~~~~~

Consider using black for automatic formatting:

.. code-block:: bash

   pip install black
   black src/

Linting
~~~~~~~

Use flake8 for linting:

.. code-block:: bash

   pip install flake8
   flake8 src/

Common Development Tasks
------------------------

Adding a New Message Type
~~~~~~~~~~~~~~~~~~~~~~~~~

1. Define message class in ``protocol/messages.py``:

.. code-block:: python

   class NewMessage(BaseMessage):
       def __init__(self, field1, field2):
           super().__init__("new_message")
           self.data["field1"] = field1
           self.data["field2"] = field2

       @classmethod
       def from_dict(cls, data):
           msg = cls(data.get("field1"), data.get("field2"))
           return msg

2. Add to ``BaseMessage.from_dict()`` dispatch:

.. code-block:: python

   elif msg_type == "new_message":
       return NewMessage.from_dict(data)

3. Add tests in ``tests/test_messages.py``

4. Update protocol documentation

Adding a New Configuration Option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Add to appropriate section in config parsing (``core/config.py``):

.. code-block:: python

   if config_obj.has_section('server'):
       if 'new_option' in config_obj['server']:
           args.new_option = config_obj['server']['new_option']

2. Add command-line argument:

.. code-block:: python

   parser.add_argument('--new-option', type=str, help='Description')

3. Add default value if not specified

4. Update configuration documentation

5. Add tests for new option

Adding Authentication Method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create new method in ``security/auth.py``
2. Update protocol to support new auth type
3. Add configuration options
4. Write comprehensive tests
5. Update security documentation

Debugging
---------

Using Debug Mode
~~~~~~~~~~~~~~~~

.. code-block:: bash

   export PADRELAY_DEBUG=1
   python -m padrelay.scripts.server --config server_config.ini

Using Python Debugger
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pdb; pdb.set_trace()

Or use VS Code debugger with launch configuration:

.. code-block:: json

   {
       "version": "0.2.0",
       "configurations": [
           {
               "name": "PadRelay Server",
               "type": "python",
               "request": "launch",
               "module": "padrelay.scripts.server",
               "args": ["--config", "config/server_config.ini"],
               "console": "integratedTerminal"
           }
       ]
   }

Logging
~~~~~~~

Add debug logging:

.. code-block:: python

   from padrelay.core.logging_utils import get_logger

   logger = get_logger(__name__)
   logger.debug("Debug message")
   logger.info("Info message")
   logger.warning("Warning message")
   logger.error("Error message")

Performance Profiling
---------------------

Using cProfile
~~~~~~~~~~~~~~

.. code-block:: bash

   python -m cProfile -o profile.stats -m padrelay.scripts.server --config server_config.ini

Analyze results:

.. code-block:: python

   import pstats
   p = pstats.Stats('profile.stats')
   p.sort_stats('cumulative')
   p.print_stats(20)

Memory Profiling
~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install memory_profiler
   python -m memory_profiler padrelay/scripts/server.py

Building Documentation
----------------------

Install Sphinx
~~~~~~~~~~~~~~

.. code-block:: bash

   pip install sphinx sphinx_rtd_theme

Build HTML Documentation
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   make html

View at ``docs/_build/html/index.html``.

Build PDF Documentation
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   make latexpdf

Requires LaTeX installation.

Release Process
---------------

Version Numbering
~~~~~~~~~~~~~~~~~

PadRelay follows Semantic Versioning:

* MAJOR.MINOR.PATCH (e.g., 1.1.0)
* MAJOR: Breaking changes
* MINOR: New features, backward compatible
* PATCH: Bug fixes, backward compatible

Creating a Release
~~~~~~~~~~~~~~~~~~

1. **Update version** in ``pyproject.toml``

2. **Update CHANGELOG.md** with release notes

3. **Run all tests:**

   .. code-block:: bash

      pytest

4. **Commit changes:**

   .. code-block:: bash

      git add pyproject.toml CHANGELOG.md
      git commit -m "Bump version to 1.x.x"

5. **Create git tag:**

   .. code-block:: bash

      git tag -a v1.x.x -m "Release version 1.x.x"

6. **Push to GitHub:**

   .. code-block:: bash

      git push origin main
      git push origin v1.x.x

7. **GitHub Actions** automatically builds and publishes to PyPI

Manual PyPI Upload
~~~~~~~~~~~~~~~~~~

If needed, manually upload to PyPI:

.. code-block:: bash

   pip install build twine
   python -m build
   twine upload dist/*

Contributing
------------

See :doc:`contributing` for contribution guidelines.

Architecture Documentation
--------------------------

See :doc:`architecture` for system architecture details.

Security Considerations
-----------------------

When developing security-related features:

* Never log passwords or tokens
* Use constant-time comparisons for secrets
* Follow OWASP guidelines
* Get security review for major changes
* Write security-focused tests

Useful Resources
----------------

* `Python asyncio documentation <https://docs.python.org/3/library/asyncio.html>`_
* `pygame documentation <https://www.pygame.org/docs/>`_
* `vgamepad documentation <https://pypi.org/project/vgamepad/>`_
* `PBKDF2 specification <https://tools.ietf.org/html/rfc2898>`_
* `TLS best practices <https://wiki.mozilla.org/Security/Server_Side_TLS>`_

See Also
--------

* :doc:`contributing` - Contribution guidelines
* :doc:`architecture` - Architecture documentation
* :doc:`api` - API reference
