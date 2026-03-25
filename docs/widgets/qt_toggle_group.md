# QtToggleGroup

`QtToggleGroup` wraps a `QButtonGroup` in a small framed widget and exposes a
friendlier value-based API.

It supports:

- exclusive selection, where `value` is a single string
- non-exclusive selection, where `value` is a list of strings
- schema-based construction through `from_schema`

```python
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_toggle_group import QtToggleGroup

app = QApplication([])

window = QWidget()
layout = QVBoxLayout(window)

exclusive = QtToggleGroup(None, options=["Fast", "Balanced", "Accurate"], value="Balanced")
exclusive.evt_changed.connect(lambda value: print("exclusive:", value))
layout.addWidget(exclusive)

multi = QtToggleGroup(None, options=["CSV", "JSON", "HTML"], value=["CSV", "JSON"], exclusive=False)
multi.evt_changed.connect(lambda value: print("multi:", value))
layout.addWidget(multi)

THEMES.apply(window)
window.show()
app.exec_()
```

## Notes

- Read the current selection from `value`.
- Read the selected button position from `index`.
- Call `setValue(...)` when you want a Qt-style setter name.

{{ show_members('qtextra.widgets.qt_toggle_group.QtToggleGroup') }}
