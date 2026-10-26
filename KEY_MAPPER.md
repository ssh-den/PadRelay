# Controller Mapping

The maintained guide is [docs/user_guide/key_mapper.rst](docs/user_guide/key_mapper.rst)
([HTML version](https://ssh-den.github.io/PadRelay/user_guide/key_mapper.html)).

Run on the machine with the physical controller:

```sh
padrelay-keymapper --output controller.ini
```

The mapper uses the first pygame controller; it has no `--joystick-index` flag.
Its other option is `--polling-interval`, defaulting to 0.1 seconds.

The generated file includes server defaults and mappings, but no password or
client trust settings. Merge its mapping sections into the **server** INI;
keep the client's network and certificate settings separate. Hat sections may
be generated but are not currently applied by the server.
