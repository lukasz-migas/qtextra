# QtCountdownWidget

A compact widget that displays remaining time until an upcoming event — useful for
notifying users about imminent updates, restarts, or scheduled changes.

## Screenshot

{{ show_example('qt_countdown.py', 520) }}

## Example

Source: `examples/qt_countdown.py`

{{ include_example('qt_countdown.py') }}

## Notes

- The progress bar fills from left to right as time elapses; it is empty at the start
  and full at expiry.
- The text label can be hidden independently of the bar so you can show a bar-only
  indicator in tight layouts.
- `tick_interval_ms` controls how often the display refreshes (default 50 ms); the
  decrement per tick is calculated automatically so the total duration is always
  respected regardless of the chosen interval.
- `evt_expired` is emitted exactly once when the countdown reaches zero and the
  internal timer stops automatically.
- Call `reset()` (optionally with a new duration) to reuse the widget for subsequent
  events without re-creating it.

## API

{{ show_members('qtextra.widgets.qt_countdown.QtCountdownWidget') }}
