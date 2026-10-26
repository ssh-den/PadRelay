# PadRelay Controller Key Mapper

The `padrelay-keymapper` command walks you through recording how your physical controller maps to a virtual Xbox 360 or DualShock 4 device. It relies on `pygame` to listen to button presses and axis movements and then writes the result to an INI configuration file.

## When should I use it?

- The default mapping does not match your controller layout.
- You want to customise which physical inputs correspond to the virtual gamepad buttons.

Generating a mapping file ensures PadRelay interprets your device correctly. The same file can be reused on any machine running PadRelay.

## Running the tool

1. Connect your controller and close any other program that might be using it.
2. Run the mapper, specifying an output file:

```bash
padrelay-keymapper --output my_config.ini
```

3. Follow the instructions:
   - The tool detects your controller and asks which virtual pad type to emulate.
   - Press each button when prompted and move each axis as directed.
   - You can skip a prompt by pressing **Enter** and edit the mapping later.
   - After all inputs are mapped you may review the mappings before saving.
   - You can also optionally invert any axes in the configuration if your controller axes do not behave correctly on the server.

## Using the generated configuration

The INI file produced by the mapper contains **only your button and axis mappings**. To apply it, run:

```bash
padrelay-server --config my_config.ini
padrelay-client --config my_config.ini
```

**Before starting the server or client**, merge in the additional server- or client-specific settings. For a detailed explanation of every setting see [the full configuration reference](CONFIGURATION.md).

