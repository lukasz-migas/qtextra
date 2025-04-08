# QtActiveOverlay

A couple of widgets that show progress by displaying an animation using a GIF or dots.

```python
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_active_overlay import QtActiveOverlay, QtActiveWidget

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

# QtActiveOverlay displays dots that are animated to show progress
layout.addWidget(
    QtActiveOverlay(
        n_dots=7,
        interval=100,  # in milliseconds
        size=30,  # size of dots
    )
)

# QtActiveWidget is simple widget with GIF playing in an infinite loop
layout.addWidget(
    QtActiveWidget(
        text="Action in progress...",
        size=(128, 128),
        which="infinity",  # also choose from dots, oval, circle, square
    )
)

widget.show()
app.exec_()
```

{{ show_widget(450) }}