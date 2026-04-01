"""QtTagManager example."""

from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra._example_helpers import section
from qtextra.config import THEMES
from qtextra.widgets.qt_button_tag import QtTagManager

app = QApplication([])
widget = QWidget()
THEMES.apply(widget)
widget.setMinimumWidth(760)

layout = QVBoxLayout(widget)
layout.setSpacing(10)

layout.addWidget(section("Editable tags"))
editable = QtTagManager(allow_action=True)
editable.add_tags(
    ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa"], hide_check=False
)
editable.add_filter(placeholder="Filter editable tags...")
editable.add_plus()
editable.add_tag("Selected", active=True, allow_action=False)
layout.addWidget(editable)

layout.addWidget(section("Selection only"))
selection = QtTagManager(allow_action=False)
selection.add_tags(["Docs", "API", "Examples", "Tests", "Theming"], hide_check=False)
selection.add_tag("Read-only", allow_check=False)
selection.add_clear()
layout.addWidget(selection)

layout.addWidget(section("Scrollable strip"))
scrollable = QtTagManager(allow_action=True, flow=False)
for index in range(10):
    scrollable.add_tag(f"Option {index}", active=index in {1, 4}, allow_action=index % 2 == 0)
scrollable.add_filter(placeholder="Find option...")
scrollable.add_plus()
layout.addWidget(scrollable)

widget.resize(700, 400)
widget.show()
app.exec_()
