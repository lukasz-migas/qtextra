# QtSegmentedButton

A unified button that combines a main text push-button (which occupies most of the width) with one or more attached icon action buttons on the right, all rendered as a single framed widget.

```
[ Main Button Text | icon1 | icon2 | ... ]
```

## Screenshot

{{ show_example('qt_button_segmented.py', 520) }}

## Example

Source: `examples/qt_button_segmented.py`

{{ include_example('qt_button_segmented.py') }}

## Notes

- Actions are appended at construction time or dynamically via `.add_action(icon_name, tooltip, func)`.
- `func` accepts a single callable or a list of callables — all are connected to the action button's `clicked` signal.
- `.add_action()` returns the `QtImagePushButton` for further customisation (e.g. setting `checkable`, changing the icon later).
- `set_flat(True)` removes the outer border, useful when placing the widget on a toolbar-style background.
- `setEnabled(False)` propagates the disabled state to all action buttons.
- The main button emits the `evt_clicked` signal; action buttons call their own callbacks independently.

## API

{{ show_members('qtextra.widgets.qt_button_segmented.QtSegmentedButton') }}
