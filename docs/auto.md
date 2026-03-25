# Automatic Widget Generation

`qtextra.auto` contains small helpers for turning lightweight schema
dictionaries into Qt widgets and for moving values between widgets and Python
data structures.

It is useful when you need:

- repetitive settings forms with predictable field types
- a simple way to hydrate widgets from saved configuration
- a matching way to collect edited values back into a dictionary

## Example

```python
from qtpy.QtWidgets import QApplication, QFormLayout, QWidget

from qtextra.auto import get_data_for_widgets, get_widget_for_schema, set_values_from_dict

app = QApplication([])

window = QWidget()
layout = QFormLayout(window)

widgets = {}
for name, schema in {
    "title": {"type": "string", "default": "Experiment A"},
    "enabled": {"type": "boolean"},
    "mode": {"type": "string", "enum": ["Fast", "Balanced", "Accurate"], "default": "Balanced"},
}.items():
    widget, extra_layout = get_widget_for_schema(window, schema)
    widgets[name] = widget
    layout.addRow(name.title(), extra_layout or widget)

set_values_from_dict({"title": "Updated name", "enabled": True}, widgets)
data = get_data_for_widgets(widgets)

window.show()
app.exec_()
```

## Notes

- `guess_widget_cls()` derives a default widget type from `type` or `anyOf`.
- `get_widget_for_schema()` returns the main widget and, when needed, a small
  wrapper layout containing help, warning, or info affordances.
- `set_values_from_dict()` and `get_data_for_widgets()` are the main
  round-tripping helpers.
