"""QtStepProgressBar."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.widgets.qt_progress_step import QtStepProgressBar

app = QApplication([])

widget = QtStepProgressBar()
THEMES.apply(widget)
widget.setMinimumWidth(500)  # to ensure it's fully visible

# add labels to the progress bar
widget.labels = ["Step One", "Step Two", "Step Three", "Step Four", "Step Five", "Complete"]
# set current step
widget.value = 3

widget.show()
app.exec_()
