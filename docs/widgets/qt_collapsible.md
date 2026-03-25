# QtCheckCollapsible

`QtCheckCollapsible` is a `superqt.QCollapsible` variant that adds a checkbox,
an action button, and a warning label to the header.

Changes from `superqt`:
- Uses a `QFormLayout` inside the collapsible content widget
- Exposes `checkbox`, `action_btn`, and `warning_label` for header-level state
- Keeps a Qt-style API with `addRow`, `addLayout`, and visibility aliases

```python
from qtpy.QtWidgets import QApplication, QLabel, QPushButton

from qtextra.config import THEMES
from qtextra.widgets.qt_collapsible import QtCheckCollapsible

app = QApplication([])
widget = QtCheckCollapsible("Advanced analysis", icon="success", warning_icon=("warning", {"color": "red"}))
THEMES.apply(widget)

# highlight hidden configuration state
widget.warning_label.setToolTip("This is a warning about something hidden within the collapsible")
# wire the action button for an auxiliary action
widget.action_btn.clicked.connect(lambda: print("Icon button clicked"))

# the content area uses a form layout
widget.addRow(QLabel("This is the inside of the collapsible frame"))
for i in range(10):
    widget.addRow(QPushButton(f"Content button {i + 1}"))
widget.expand(animate=False)
widget.show()

app.exec_()
```

{{ show_widget(350) }}

## Notes

- Use `is_checked` to inspect the header checkbox state.
- Use `setCheckboxVisible`, `setIconVisible`, and `setWarningVisible` to hide
  individual header controls.
- `addRow` requires the internal content layout to expose an `addRow` method,
  which is true for the default `QFormLayout`.

{{ show_members('qtextra.widgets.qt_collapsible.QtCheckCollapsible') }}
