"""QtCheckCollapsible"""

from qtpy.QtWidgets import QApplication, QLabel, QPushButton

from qtextra.config import THEMES
from qtextra.widgets.qt_collapsible import QtCheckCollapsible

app = QApplication([])
collapsible = QtCheckCollapsible("Advanced analysis", icon="success", warning_icon=("warning", {"color": "red"}))
# you can display warnings in the collapsible to highlight if an option needs attention
collapsible.warning_label.setToolTip("This is a warning about something hidden within the collapsible")
# you can also use the additional action button to perform an action
collapsible.action_btn.clicked.connect(lambda: print("Icon button clicked"))
# add widgets to the collapsible
collapsible.addRow(QLabel("This is the inside of the collapsible frame"))
for i in range(10):
    collapsible.addRow(QPushButton(f"Content button {i + 1}"))
collapsible.expand(animate=False)
collapsible.show()

THEMES.set_theme_stylesheet(collapsible)
app.exec_()
