Contributing
============

Submit fixes, features, documentation and controller mappings through
`GitHub pull requests <https://github.com/ssh-den/PadRelay/pulls>`_.
See :doc:`development` for local setup, checks and code organization.

Pull Requests
-------------

Keep each PR focused on one change. In the description, explain:

* The problem and the resulting behavior.
* How you verified it, including any manual hardware testing.
* Compatibility changes and any steps users need to take when upgrading.

For bug fixes, add a test that reproduces the failure. For new behavior, cover
the relevant success and failure cases. Run the checks listed in
:doc:`development` before submitting code.

Update the affected guides, configuration examples or protocol specification
when behavior changes. Add user-facing changes to ``CHANGELOG.md``. Formatting
and import order follow the tools configured in ``pyproject.toml``.

Bugs and Feature Requests
-------------------------

Open an `issue <https://github.com/ssh-den/PadRelay/issues>`_ with reproduction
steps, expected and actual behavior, PadRelay and Python versions, and the
client/server operating systems. For controller problems, include the model
and selected gamepad type. Attach relevant logs and configuration with secrets
removed.

For a feature request, describe the use case and what existing options cannot
do. A proposed implementation is optional.

Controller Mappings
-------------------

Generate mappings with ``padrelay-keymapper``; see :doc:`user_guide/key_mapper`.
Include the controller model, operating system, target gamepad type
(``xbox360`` or ``ds4``), and which buttons, sticks, triggers and D-pad inputs
you tested. Keep passwords and machine-specific paths out of shared configs.

Documentation
-------------

Guides live in ``docs/*.rst``. Update existing pages where possible and add new
pages to the appropriate toctree. Build the documentation locally using the
commands in :doc:`development` and check the changed pages in a browser.

Security Reports
----------------

Report vulnerabilities privately to `sshden@duck.com <mailto:sshden@duck.com>`_,
not in a public issue. Include the affected version, reproduction steps and
impact. Do not send real passwords, session keys or private TLS keys.

License
-------

Contributions are licensed under the project's MIT License.
