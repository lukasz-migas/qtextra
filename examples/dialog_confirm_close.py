"""QtPopout example."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_close_window import QtConfirmCloseDialog

app = QApplication([])

widget = QtConfirmCloseDialog(None, no_icon=False)
THEMES.apply(widget)
widget.show()
app.exec_()
