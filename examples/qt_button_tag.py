"""QtCheckCollapsible."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.widgets.qt_button_tag import QtTagManager

app = QApplication([])
widget = QtTagManager(allow_action=True, flow=False)
widget.setMinimumWidth(500)
THEMES.apply(widget)

# add tags to the tag manager
for i in range(7):
    widget.add_tag(f"Option {i}", active=i == 2, allow_action=True)
# add text filter to narrow down the list of options
widget.add_filter()
# add an action that will enable you to add a new tag
widget.add_plus()
widget.evt_changed.connect(lambda hash_id, state: print(f"Tag {hash_id} was {'checked' if state else 'unchecked'}"))

widget.show()
app.exec_()
