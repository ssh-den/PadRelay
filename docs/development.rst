Development
===========

Setup
-----

Use Python **3.11 or newer**. The ``Run Tests`` workflow checks Python
3.11.
From the repository root, create and activate a virtual environment named
``.venv``, then install the project and development tools:

.. code-block:: bash

   python -m pip install -e ".[dev]"

The ``.venv`` path is used by the Pyright configuration. For manual server
testing, also install the ``server`` extra and the required gamepad driver;
see :doc:`installation`. Automated tests replace gamepad hardware, so they
do not require a physical controller or ViGEmBus.

Code Organization
-----------------

* ``src/padrelay/client/`` polls the controller and sends input.
* ``src/padrelay/server/`` receives input and updates the virtual gamepad.
* ``src/padrelay/protocol/`` handles messages and TCP/UDP transport.
* ``src/padrelay/security/`` handles authentication, TLS, UDP sessions and limits.
* ``src/padrelay/core/`` parses configuration and configures logging.
* ``src/padrelay/scripts/`` contains the client, server and key mapper entry points.

The application loops are in ``client_app.py`` and ``server_app.py``.
``GamepadHandler`` translates validated messages into ``VirtualGamepad`` calls.
TCP carries input directly; UDP uses a TLS control connection to authenticate
and provision keys for encrypted input datagrams. See :doc:`architecture` and
:doc:`protocol` for the full flow.

Checks and Tests
----------------

In GitHub Actions, select ``Run Tests`` and click ``Run workflow`` to start the
checks manually. For a PR, submitting an ``Approve`` review starts tests only
when the reviewer has write, maintain or admin access and approved the current
head commit. Tests check out that exact commit with read-only token permissions.
New commits require a new approval; pushes and opening a PR do not start tests.
GitHub may additionally require approval of workflow runs from forks according
to the repository's Actions settings.

Run the same checks as CI from the repository root:

.. code-block:: bash

   ruff check .
   black --check .
   mypy
   pylint src/padrelay
   pyright
   pytest

Ruff and Black include tests and documentation Python files. Mypy, Pyright and
Pylint check production code under ``src``. Settings live in ``pyproject.toml``;
use ``black .`` to apply formatting.

For a focused test run or coverage report:

.. code-block:: bash

   pytest tests/test_udp_protocol.py
   pytest --cov=padrelay --cov-report=html

Coverage output is written to ``htmlcov/index.html``. End-to-end network tests
use real loopback sockets and TLS with temporary certificates; gamepad hardware
is replaced. For changes involving drivers or controller behavior, also test with
the affected hardware and report the operating system and controller model.

Changing Behavior
-----------------

Configuration changes belong in ``core/config.py``. Cover CLI, INI and
environment-variable handling in tests, and update :doc:`configuration` plus
the affected files under ``config/``.

Message changes belong in ``protocol/messages.py`` and the relevant transport
handler. Keep client and server changes together, test malformed input and
compatibility, and update :doc:`protocol`. Changes to authentication, encryption
or resource limits also need negative tests and an update to :doc:`security`.

Comments and docstrings should explain constraints and non-obvious behavior.
The API reference is generated from signatures and docstrings; CLI and
configuration guides are maintained separately.

Running and Debugging
---------------------

The editable install provides ``padrelay-client``, ``padrelay-server`` and
``padrelay-keymapper``. Use :doc:`quickstart` for runtime configuration and
:doc:`user_guide/tls_setup` for certificate trust setup.

Set ``PADRELAY_DEBUG=1`` before starting a process to enable debug logging.
Logs are written to ``~/.padrelay/logs/padrelay.log`` by default; set
``PADRELAY_LOG_DIR`` to use another directory. Never add passwords, session
keys or private TLS keys to log output.

Documentation
-------------

Install the documentation dependencies and build HTML from the repository root:

.. code-block:: bash

   python -m pip install -r docs/requirements.txt
   python -m sphinx -b html docs docs/_build/html

Open ``docs/_build/html/index.html`` and review the changed pages. New pages
need a toctree entry. Publishing is separate: the manual ``Documentation``
workflow builds committed sources on ``main`` and deploys them to GitHub Pages.

Releases
--------

Maintainers update ``pyproject.toml`` and ``CHANGELOG.md``, then push to ``main``.
In GitHub Actions, select ``Build and Release``, click ``Run workflow`` and
choose ``main``. Leave the release tag field blank to use ``v<version>`` from
``pyproject.toml``, or enter that exact tag explicitly. A different tag stops
the workflow before dependencies and tests run. The version is read at runtime;
it is not hardcoded in the workflow. No existing tag is required; pushing alone
does not publish.
The workflow runs the static checks and tests on Python 3.11 before building
and publishing. All checks must pass for the release to proceed.
The package version must have a dated changelog entry. The workflow checks this
before building and validates the distribution metadata before upload.
The workflow uploads to PyPI using OIDC Trusted Publishing before creating the
GitHub release and its ``v<version>`` tag (``v3.0.0`` for ``3.0.0``) at the
commit selected for the run. No PyPI API token or repository secret is required.

See the `PyPI Trusted Publisher setup guide
<https://docs.pypi.org/trusted-publishers/adding-a-publisher/>`_. Published PyPI versions cannot be overwritten.

For pull request expectations and reporting bugs, see :doc:`contributing`.
