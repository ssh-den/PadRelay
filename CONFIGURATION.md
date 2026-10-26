# Configuration

The maintained option tables, defaults, credential precedence and mapping rules
are in [docs/configuration.rst](docs/configuration.rst)
([HTML reference](https://ssh-den.github.io/PadRelay/configuration.html)).

Templates are in [config/](config/). Load one explicitly with `--config`; keep
server and client files separate. Use standalone comment lines in INI files.

TCP uses verified TLS by default. UDP v2 requires password authentication and
verified TLS control on the same numeric TCP port as its UDP input port.
Configure client certificate trust and allow **both TCP and UDP** for UDP mode.
See [certificate setup](docs/user_guide/tls_setup.rst) and the
[quick start](docs/quickstart.rst) for complete examples.

Run the installed command's `--help` for its flags. Use `python -m pip show
padrelay` to check its version; there is no PadRelay `--version` flag.
