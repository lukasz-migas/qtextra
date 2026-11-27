# QtCommandPalette

A lazy, searchable popup for menu actions and custom commands.

## Screenshot

{{ show_example('qt_command_palette.py', 700) }}

## Example

Source: `examples/qt_command_palette.py`

{{ include_example('qt_command_palette.py') }}
## Notes

- Call `QtCommandPalette.install(window)` during setup. The first open creates the popup. Each open discovers the visible, enabled actions already present in the window's menu bar.
- Open it with Ctrl+Shift+P (Cmd+Shift+P on macOS) or call `palette.open()`. Pass `shortcut=None` to disable the opening shortcut.
- Use `add_command()` for a callback or `add_action()` to reuse an existing QAction. Keep the returned handle if you need to call `remove_command()` when unloading a plugin.
- Construct `QtCommandPalette(parent)` directly to use the popup from a dialog or other QWidget.

## API

{{ show_members('qtextra.widgets.qt_command_palette.QtCommandPalette') }}

{{ show_members('qtextra.widgets.qt_command_palette.CommandPaletteController') }}
