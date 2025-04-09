"""QtStepProgressBar."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.widgets.qt_system_summary import QtSystemSummaryWidget

app = QApplication([])

widget = QtSystemSummaryWidget()
THEMES.apply(widget)
widget.setMinimumWidth(500)  # to ensure it's fully visible

widget.show()
app.exec_()
