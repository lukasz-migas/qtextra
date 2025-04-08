"""QtPopout example."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_color_dialog import QtColorListDialog

app = QApplication([])

widget = QtColorListDialog(None, ["#FF0000", "#00FF00", "#0000FF"], "Select a color")
THEMES.apply(widget)
widget.show()
app.exec_()
