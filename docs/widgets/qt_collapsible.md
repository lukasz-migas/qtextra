# QtCheckCollapsible

Collapsible `QFrame` that can be expanded or collapsed by clicking on the header.

It can contain any widget, and it is useful for organizing the layout of a window or dialog.

This is a slightly modified version of the `QCollapsible` class from `superqt`, which is a Qt widget library.

Changes from `superqt`:
- Changed layout type to be `QFormLayout` instead of `QVBoxLayout`.'
- Added `action_btn` to the header to allow for an additional action button.
- Added `warning_label` to the header to allow for a warning icon and tooltip.

```python
from qtpy.QtWidgets import QApplication, QLabel, QPushButton

from qtextra.config import THEMES
from qtextra.widgets.qt_collapsible import QtCheckCollapsible

app = QApplication([])
collapsible = QtCheckCollapsible("Advanced analysis", icon="success", warning_icon=("warning", {"color": "red"}))
THEMES.set_theme_stylesheet(collapsible)

# you can display warnings in the collapsible to highlight if an option needs attention
collapsible.warning_label.setToolTip("This is a warning about something hidden within the collapsible")
# you can also use the additional action button to perform an action
collapsible.action_btn.clicked.connect(lambda: print("Icon button clicked"))
# add widgets to the collapsible
collapsible.addRow(QLabel("This is the inside of the collapsible frame"))
for i in range(10):
    collapsible.addRow(QPushButton(f"Content button {i + 1}"))
collapsible.expand(animate=False)
collapsible.show()

app.exec_()
```

{{ show_widget(350) }}

{{ show_members('qtextra.widgets.qt_collapsible.QtCheckCollapsible') }}
