# QtPanelToolbar

A vertical toolbar that toggles stacked panels, with optional labelled buttons.

Pass `size_preset` to control the button and icon size and make the toolbar more compact. For example,
`QtPanelToolbar(parent, size_preset="24px")` uses 24-pixel buttons. Individual buttons can override the toolbar
preset with `add_widget(..., size_preset="40px")`.

## Screenshot

{{ show_example('qt_toolbar_panel.py', 620) }}

## Example

Source: `examples/qt_toolbar_panel.py`

{{ include_example('qt_toolbar_panel.py') }}

## API

{{ show_members('qtextra.widgets.qt_toolbar_panel.QtPanelToolbar') }}

{{ show_members('qtextra.widgets.qt_toolbar_panel.QtPanelWidget') }}
