# Documentation

Sphinx builds the `.rst` guides and the API reference. Read the
[development guide](development.rst) for the contributor setup and checks.

## Build

From the repository root, with PadRelay installed in the active environment:

```sh
python -m pip install -r docs/requirements.txt
python -m sphinx -b html docs docs/_build/html
```

Open `docs/_build/html/index.html`. For a strict build, add `-W --keep-going`.
New pages need an entry in a toctree. API signatures and docstrings come from
source through autodoc; CLI tables, examples and behavioral descriptions are
maintained manually.

## Page Ownership

- `quickstart.rst`: one complete first connection and the UDP migration steps.
- `configuration.rst`: settings, defaults, precedence and mapping semantics.
- `user_guide/tls_setup.rst`: trust distribution, identity files and renewal.
- `user_guide/client.rst`, `server.rst`, `key_mapper.rst`: operation-specific details.
- `user_guide/troubleshooting.rst`: diagnosis by symptom.
- `protocol.rst`: byte encodings, message shapes and timing.
- `security.rst`: protection and resource boundaries.
- `architecture.rst`, `api.rst`: code organization and Python interfaces.
- `development.rst`, `contributing.rst`: local work and submitting changes.

Link to the owning page rather than copying its option tables or setup steps.
The root `CONFIGURATION.md` and `KEY_MAPPER.md` point to those same guides.

## Publish

The manual **Documentation** workflow builds committed sources on `main` and
deploys [GitHub Pages](https://ssh-den.github.io/PadRelay/). Local edits and builds
do not update the site. GitHub Pages must use GitHub Actions as its source.

**Run Tests** runs on pushes, pull requests and manual dispatch.
**Build and Release** is manual against an existing `v*` tag; it publishes to
PyPI before creating the GitHub release. See `.github/workflows/` for the actual
triggers and permissions.
