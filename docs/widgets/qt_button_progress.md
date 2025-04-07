# QtActiveProgressBarButton

Button with progress bar and activity indicator.


```python
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_button_progress import QtActiveProgressBarButton

app = QApplication([])

widget = QWidget()
THEMES.set_theme_stylesheet(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

active_btn = QtActiveProgressBarButton(widget, "Click me")
active_btn.setRange(0, 100)
active_btn.setValue(10)
active_btn.active = True
layout.addWidget(active_btn)

active_btn = QtActiveProgressBarButton(widget, "Click me")
active_btn.setRange(0, 100)
active_btn.setValue(10)
layout.addWidget(active_btn)
widget.show()

app.exec_()
```

{{ show_widget(350) }}

{{ show_members('qtextra.widgets.qt_button_progress.QtActiveProgressBarButton') }}
