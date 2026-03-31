# QtOverlay

Overlay widgets attach floating labels or message boxes to another widget
without changing that widget's layout.

```python
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_overlay import QtOverlayDismissMessage, QtOverlayLabel

app = QApplication([])

widget = QWidget()
widget.setWindowTitle("QtOverlay Example")
THEMES.apply(widget)

layout = QVBoxLayout(widget)
editor = QTextEdit()
editor.setPlaceholderText("Overlay target")
layout.addWidget(editor)

hint = QtOverlayLabel(
    parent=widget,
    widget=editor,
    text="Autosave is enabled",
    alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
)

message = QtOverlayDismissMessage(
    parent=widget,
    widget=editor,
    icon_name="info",
    text="This editor is read-only until the file finishes loading.",
    word_wrap=True,
    dismiss_btn=True,
    ok_btn=True,
    ok_text="Understood",
)
message.display()

widget.resize(520, 320)
widget.show()
app.exec_()
```

Use `QtOverlayLabel` for small contextual hints and `QtOverlayMessage` or
`QtOverlayDismissMessage` when you need actions such as dismiss or accept.
Overlays automatically follow the anchor widget when it moves, resizes, shows,
or hides.
