"""QtPopout example."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_text_replace import QtTextReplace

app = QApplication([])

widget = QtTextReplace(
    None,
    [
        "This is a first text.",
        "This is a second text.",
        "This is a third text.",
    ],
)
widget.add("first", "FIRST")
widget.add("third", "3")
THEMES.apply(widget)
widget.show()
app.exec_()
