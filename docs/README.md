# PadRelay Documentation

This directory contains the complete documentation for PadRelay, built with Sphinx and hosted on ReadTheDocs.

## Building the Documentation

### Prerequisites

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Build HTML Documentation

```bash
cd docs
make html
```

The generated documentation will be in `_build/html/`. Open `_build/html/index.html` in your browser.

### Build PDF Documentation

```bash
cd docs
make latexpdf
```

Requires LaTeX installation.

### Other Formats

```bash
make epub    # ePub format
make text    # Plain text
make man     # Man pages
```

## Documentation Structure

```
docs/
├── index.rst                  # Main documentation index
├── installation.rst           # Installation guide
├── quickstart.rst             # Quick start guide
├── configuration.rst          # Configuration reference
├── architecture.rst           # System architecture
├── security.rst               # Security documentation
├── protocol.rst               # Protocol specification
├── api.rst                    # API reference
├── development.rst            # Development guide
├── contributing.rst           # Contributing guidelines
├── changelog.rst              # Changelog
├── user_guide/                # User guides
│   ├── client.rst            # Client guide
│   ├── server.rst            # Server guide
│   ├── key_mapper.rst        # Key mapper guide
│   ├── tls_setup.rst         # TLS setup guide
│   └── troubleshooting.rst   # Troubleshooting guide
├── conf.py                    # Sphinx configuration
├── requirements.txt           # Documentation dependencies
├── Makefile                   # Unix build script
└── make.bat                   # Windows build script
```

## Online Documentation

The documentation is automatically built and published to:

* **ReadTheDocs:** https://padrelay.readthedocs.io
* **GitHub Pages:** https://ssh-den.github.io/PadRelay

## Continuous Integration

Documentation is automatically built and validated on every pull request via GitHub Actions. The workflow:

1. Builds HTML documentation with Sphinx
2. Checks for broken links
3. Uploads build artifacts
4. Deploys to GitHub Pages (on main branch)

See `.github/workflows/docs.yml` for the workflow configuration.

## Writing Documentation

### reStructuredText Format

Documentation uses reStructuredText (reST) format. Key syntax:

**Headers:**
```rst
Title
=====

Section
-------

Subsection
~~~~~~~~~~
```

**Code Blocks:**
```rst
.. code-block:: python

   def hello():
       print("Hello, World!")
```

**Links:**
```rst
:doc:`installation`  # Internal link
`External Link <https://example.com>`_
```

**Admonitions:**
```rst
.. note::
   This is a note

.. warning::
   This is a warning

.. important::
   This is important
```

### Adding New Pages

1. Create a new `.rst` file in the appropriate directory
2. Add it to the `toctree` in `index.rst` or the relevant parent document
3. Build and verify the documentation

### API Documentation

API documentation is automatically generated from docstrings using Sphinx's autodoc extension. Write docstrings in Google style:

```python
def function(arg1: str, arg2: int) -> bool:
    """Brief description.

    Longer description with more details.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When something is wrong
    """
    pass
```

## Troubleshooting

### Build Errors

**"sphinx-build: command not found"**

Install Sphinx:
```bash
pip install sphinx
```

**Import errors during autodoc**

Ensure the project is installed:
```bash
pip install -e ..
```

**"vgamepad not found" on Linux/macOS**

vgamepad is Windows-only. Autodoc will skip it automatically, but you may see warnings.

### Link Check Failures

Some external links may be temporarily unavailable. Review `_build/linkcheck/output.txt` for details.

## Contributing

See `contributing.rst` for guidelines on contributing to the documentation.

## License

The documentation is licensed under the MIT License, same as the project.
