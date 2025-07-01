"""QtCheckCollapsible."""

from qtpy.QtWidgets import QApplication, QLabel, QPushButton

from qtextra.config import THEMES
from qtextra.widgets.qt_collapsible import QtCheckCollapsible

app = QApplication([])
widget = QtCheckCollapsible("Advanced analysis", icon="settings", warning_icon=("warning", {"color": "red"}))
THEMES.apply(widget)

# you can display warnings in the collapsible to highlight if an option needs attention
widget.warning_label.setToolTip("This is a warning about something hidden within the collapsible")
# you can also use the additional action button to perform an action
widget.action_btn.clicked.connect(lambda: print("Icon button clicked"))
# add widgets to the collapsible
widget.addRow(QLabel("This is the inside of the collapsible frame"))
for i in range(10):
    widget.addRow(QPushButton(f"Content button {i + 1}"))
widget.expand(animate=False)
widget.show()

app.exec_()
