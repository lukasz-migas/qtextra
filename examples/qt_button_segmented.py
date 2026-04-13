"""QtSegmentedButton example."""

from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra._example_helpers import section
from qtextra.config import THEMES
from qtextra.widgets.qt_button_segmented import QtSegmentedButton

app = QApplication([])
widget = QWidget()
THEMES.apply(widget)
widget.setMinimumWidth(520)

layout = QVBoxLayout(widget)
layout.setSpacing(10)

layout.addWidget(section("Basic — main button with two actions"))
basic = QtSegmentedButton("Run pipeline", widget)
basic.evt_clicked.connect(lambda: print("Run clicked"))
basic.add_action("settings", "Configure run", lambda: print("Settings clicked"))
basic.add_action("close", "Cancel run", lambda: print("Cancel clicked"))
layout.addWidget(basic)

layout.addWidget(section("Multiple actions"))
export = QtSegmentedButton("Export", widget)
export.evt_clicked.connect(lambda: print("Export clicked"))
export.add_action("save", "Save to file", lambda: print("Save clicked"))
export.add_action("copy", "Copy to clipboard", lambda: print("Copy clicked"))
export.add_action("delete", "Discard", lambda: print("Discard clicked"))
layout.addWidget(export)

layout.addWidget(section("Flat style (no border)"))
flat = QtSegmentedButton("Process", widget, flat=True)
flat.evt_clicked.connect(lambda: print("Process clicked"))
flat.add_action("add", "Add item", lambda: print("Add clicked"))
flat.add_action("refresh", "Refresh", lambda: print("Refresh clicked"))
layout.addWidget(flat)

layout.addWidget(section("Disabled"))
disabled = QtSegmentedButton("Unavailable", widget)
disabled.add_action("settings", "Configure")
disabled.add_action("close", "Cancel")
disabled.setEnabled(False)
layout.addWidget(disabled)

layout.addWidget(section("No actions — degrades to plain button"))
plain = QtSegmentedButton("Submit", widget)
plain.evt_clicked.connect(lambda: print("Submit clicked"))
layout.addWidget(plain)

layout.addStretch()
widget.resize(520, 340)
widget.show()
app.exec_()
