# QtFloatingProgressBar

Floating progress overlay with a status label and progress bar, anchored to another widget.

## Screenshot

{{ show_example('qt_floating_progress_bar.py', 620) }}

## Example

Source: `examples/qt_floating_progress_bar.py`

{{ include_example('qt_floating_progress_bar.py') }}

## Notes

- The overlay remains inside the host widget's coordinate space, so it moves with a window or dialog.
- Use `set_busy(True)` to switch the bar into indeterminate mode when total progress is unknown.
- Attach it either to a child content widget or directly to a top-level dialog or main window.

## API

{{ show_members('qtextra.widgets.qt_floating_progress_bar.QtFloatingProgressBar') }}
