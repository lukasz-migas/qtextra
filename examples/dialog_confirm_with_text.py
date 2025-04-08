"""QtPopout example."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_confirm import QtConfirmWithTextDialog

app = QApplication([])

widget = QtConfirmWithTextDialog(None, message="Please type 'qtextra' to continue", request="qtextra")
THEMES.apply(widget)
widget.show()
app.exec_()
