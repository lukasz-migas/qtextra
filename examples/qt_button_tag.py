"""QtCheckCollapsible"""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.widgets.qt_button_tag import QtTagManager

app = QApplication([])
widget = QtTagManager(allow_action=True)
widget.setMinimumWidth(500)
THEMES.apply(widget)

# add tags to the tag manager
for i in range(5):
    widget.add_tag(f"Tag number: {i}", active=i == 2, allow_action=True)
# add an action that will enable you to add a new tag
widget.add_plus()
widget.evt_changed.connect(lambda hash_id, state: print(f"Tag {hash_id} was {'checked' if state else 'unchecked'}"))

widget.show()
app.exec_()
