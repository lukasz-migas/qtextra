# QtCircularCountdownWidget

A circular countdown that shows the time remaining until an event. It works in
compact layouts, including at 20 x 20 pixels.

## Example

Source: `examples/qt_countdown.py`

{{ include_example('qt_countdown.py') }}

## Notes

- Pass a duration in milliseconds. Call `start()`, `pause()`, and `stop()` to
  control the countdown; stopping resets it to the full duration.
- Use `set_duration()` to set a new duration and reset the countdown.
- Set `show_time=True` to display the remaining time when it fits in the ring.
  Text is hidden automatically when the widget is too small.
- Set `auto_hide=True` to hide the widget on expiry. Starting it again shows it.
- Connect to `evt_expired` to react when the countdown reaches zero.

## API

{{ show_members('qtextra.widgets.qt_countdown.QtCircularCountdownWidget') }}
