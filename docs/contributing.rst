Contributing Guide
==================

Thank you for considering contributing to PadRelay! This document provides guidelines for contributing.

Ways to Contribute
------------------

* **Report bugs:** Open GitHub issues for bugs or unexpected behavior
* **Suggest features:** Propose new features or improvements
* **Write documentation:** Improve or expand documentation
* **Submit code:** Fix bugs or implement new features
* **Share controller mappings:** Contribute mappings for different controllers
* **Help others:** Answer questions in GitHub issues

Getting Started
---------------

1. Fork the Repository
~~~~~~~~~~~~~~~~~~~~~~~

Fork PadRelay on GitHub: https://github.com/ssh-den/PadRelay

2. Clone Your Fork
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/YOUR_USERNAME/PadRelay.git
   cd PadRelay

3. Set Up Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows

   pip install -e .
   pip install pytest pytest-asyncio

4. Create a Branch
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git checkout -b feature/my-feature
   # or
   git checkout -b fix/bug-description

Contribution Workflow
---------------------

1. Make Changes
~~~~~~~~~~~~~~~

* Follow coding standards (see :doc:`development`)
* Write tests for new code
* Update documentation as needed
* Keep commits focused and atomic

2. Test Your Changes
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run specific tests
   pytest tests/test_auth.py

   # Check coverage
   pytest --cov=padrelay

Ensure all tests pass before submitting.

3. Commit Your Changes
~~~~~~~~~~~~~~~~~~~~~~~

Write clear commit messages:

.. code-block:: bash

   git add .
   git commit -m "Add feature X that does Y

   - Implemented feature Z
   - Added tests for feature Z
   - Updated documentation"

**Commit Message Guidelines:**

* Use present tense ("Add feature" not "Added feature")
* First line: Brief summary (50 characters or less)
* Blank line after first line
* Detailed explanation if needed
* Reference issues: "Fixes #123" or "Closes #456"

4. Push to Your Fork
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git push origin feature/my-feature

5. Create Pull Request
~~~~~~~~~~~~~~~~~~~~~~

1. Go to the original PadRelay repository
2. Click "Pull Requests" → "New Pull Request"
3. Click "compare across forks"
4. Select your fork and branch
5. Fill in the PR template (see below)
6. Submit the pull request

Pull Request Guidelines
-----------------------

PR Template
~~~~~~~~~~~

When creating a pull request, include:

.. code-block:: markdown

   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Performance improvement
   - [ ] Code refactoring

   ## Testing
   - [ ] All tests pass
   - [ ] Added tests for new code
   - [ ] Tested manually

   ## Checklist
   - [ ] Code follows project style guidelines
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated (for user-facing changes)
   - [ ] No breaking changes (or documented if necessary)

   ## Related Issues
   Fixes #123

PR Review Process
~~~~~~~~~~~~~~~~~

1. **Automated checks:** CI runs tests automatically
2. **Code review:** Maintainer reviews code
3. **Revisions:** Address review comments if needed
4. **Approval:** Maintainer approves PR
5. **Merge:** Maintainer merges into main branch

Code Style
----------

Follow these guidelines:

Python Style
~~~~~~~~~~~~

* Follow PEP 8 with 100-character line length
* Use type hints for function signatures
* Use f-strings for string formatting
* Use double quotes for strings
* Sort imports alphabetically

Example:

.. code-block:: python

   from typing import Optional

   def authenticate(password: str, challenge: Optional[bytes] = None) -> bool:
       """Authenticate using password and challenge.

       Args:
           password: User password
           challenge: Optional challenge bytes

       Returns:
           True if authentication successful
       """
       if challenge is None:
           challenge = generate_challenge()
       return verify(password, challenge)

Documentation Style
~~~~~~~~~~~~~~~~~~~

* Use reStructuredText format
* Include code examples
* Keep line length reasonable (80-100 characters)
* Use proper Sphinx directives

Testing Guidelines
------------------

Write Tests
~~~~~~~~~~~

All new code should have tests:

.. code-block:: python

   import pytest
   from padrelay.security.auth import Authenticator

   def test_hash_password():
       """Test password hashing."""
       password = "test_password"
       hash1 = Authenticator.hash_password(password)
       hash2 = Authenticator.hash_password(password)

       # Hashes should differ (random salt)
       assert hash1 != hash2

       # Both should be valid hash strings
       assert Authenticator._is_hash_string(hash1)
       assert Authenticator._is_hash_string(hash2)

Test Coverage
~~~~~~~~~~~~~

* Aim for >80% code coverage
* Test both success and failure cases
* Test edge cases and boundary conditions
* Test error handling

Bug Reports
-----------

Reporting Bugs
~~~~~~~~~~~~~~

When reporting bugs, include:

1. **Description:** Clear description of the bug
2. **Steps to Reproduce:**

   * Step 1
   * Step 2
   * Step 3

3. **Expected Behavior:** What should happen
4. **Actual Behavior:** What actually happens
5. **Environment:**

   * PadRelay version
   * Operating system
   * Python version

6. **Logs:** Relevant log output (with debug mode enabled)
7. **Configuration:** Sanitized config files (remove passwords)

Example Bug Report
~~~~~~~~~~~~~~~~~~

.. code-block:: markdown

   **Bug Description**
   Client fails to reconnect after server restart

   **Steps to Reproduce**
   1. Start server with `padrelay-server --config server.ini`
   2. Start client with `padrelay-client --config client.ini`
   3. Stop server with Ctrl+C
   4. Restart server
   5. Client does not reconnect

   **Expected Behavior**
   Client should automatically reconnect after server restarts

   **Actual Behavior**
   Client shows "Connection refused" and does not retry

   **Environment**
   - PadRelay version: 1.1.0
   - Client OS: Ubuntu 22.04
   - Server OS: Windows 11
   - Python: 3.10.0

   **Logs**
   ```
   ERROR: Connection refused to 192.168.1.100:9999
   ```

Feature Requests
----------------

Proposing Features
~~~~~~~~~~~~~~~~~~

When suggesting features, include:

1. **Use Case:** Why is this feature needed?
2. **Description:** What should the feature do?
3. **Implementation Ideas:** How might it work?
4. **Alternatives:** What alternatives have you considered?

Example Feature Request
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: markdown

   **Feature Request: Multi-Gamepad Support**

   **Use Case**
   I want to use two gamepads simultaneously on the same Windows machine
   for local multiplayer games.

   **Description**
   Allow running multiple server instances, each creating a separate
   virtual gamepad for different clients.

   **Implementation Ideas**
   - Allow server to create multiple virtual gamepads
   - Assign each connected client to a different virtual gamepad
   - Add configuration option for max gamepads

   **Alternatives**
   - Run multiple server instances on different ports
   - Use multiple Windows machines

Documentation Contributions
---------------------------

Types of Documentation
~~~~~~~~~~~~~~~~~~~~~~

* **User documentation:** Guides, tutorials, how-tos
* **Developer documentation:** Architecture, API, development guides
* **Code comments:** Inline documentation
* **Examples:** Sample configurations, scripts

Documentation Standards
~~~~~~~~~~~~~~~~~~~~~~~

* Clear and concise language
* Include examples
* Keep documentation up-to-date with code
* Use proper reStructuredText formatting

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   pip install sphinx sphinx_rtd_theme
   make html

View at ``docs/_build/html/index.html``.

Controller Mapping Contributions
---------------------------------

Share Your Mappings
~~~~~~~~~~~~~~~~~~~

If you've created a mapping for a controller, share it:

1. Create mapping with key mapper
2. Test thoroughly
3. Create PR adding mapping to ``config/mappings/`` directory
4. Include controller name and model in filename

Example PR:

.. code-block:: bash

   config/mappings/logitech_f310_xbox360.ini
   config/mappings/sony_dualshock4_ds4.ini

Code Review Guidelines
----------------------

For Reviewers
~~~~~~~~~~~~~

When reviewing PRs:

* Be constructive and respectful
* Explain why changes are needed
* Suggest specific improvements
* Acknowledge good work
* Test the changes if possible

For Contributors
~~~~~~~~~~~~~~~~

When receiving feedback:

* Be open to suggestions
* Ask questions if unclear
* Make requested changes promptly
* Thank reviewers for their time

Security Contributions
----------------------

Reporting Security Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Do not open public issues for security vulnerabilities.**

Instead:

1. Email: sshden@duck.com
2. Include:

   * Vulnerability description
   * Impact assessment
   * Proof of concept (if applicable)
   * Suggested fix

3. Allow time for patch before public disclosure

Security Contributions
~~~~~~~~~~~~~~~~~~~~~~

When contributing security features:

* Get code review from multiple developers
* Write comprehensive tests
* Document security implications
* Follow security best practices

License
-------

By contributing, you agree that your contributions will be licensed under the MIT License.

Code of Conduct
---------------

We expect all contributors to:

* Be respectful and inclusive
* Welcome newcomers
* Accept constructive criticism
* Focus on what's best for the project
* Show empathy towards others

Unacceptable behavior includes:

* Harassment or discrimination
* Trolling or insulting comments
* Personal or political attacks
* Publishing others' private information

Questions?
----------

If you have questions about contributing:

* Open a GitHub issue with the "question" label
* Email: sshden@duck.com
* Check existing documentation

Thank You!
----------

Thank you for contributing to PadRelay! Your contributions help make the project better for everyone.

See Also
--------

* :doc:`development` - Development guide
* :doc:`architecture` - Architecture documentation
* `GitHub Repository <https://github.com/ssh-den/PadRelay>`_
