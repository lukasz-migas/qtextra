"""QtActiveProgressBarButton"""

from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar

app = QApplication([])

widget = QWidget()
widget.setMinimumWidth(500)
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

layout.addWidget(horz_toolbar := QtMiniToolbar(widget, orientation="horizontal", add_spacer=False))
layout.addWidget(vert_toolbar := QtMiniToolbar(widget, orientation="vertical", add_spacer=False))

# add tools
for icon in ["home", "settings", "help", "info", "warning", "error"]:
    horz_toolbar.add_qta_tool(icon, tooltip=icon, func=None)
    vert_toolbar.add_qta_tool(icon, tooltip=icon, func=None)

# you can also add separator
horz_toolbar.add_separator()
# or spacer
horz_toolbar.add_spacer()
# and then add more tools
horz_toolbar.add_qta_tool("color_palette", tooltip="color_palette", func=None)
# you can also insert tools
horz_toolbar.insert_qta_tool("chevron_up", 3, tooltip="chevron_up", func=None)


layout.addStretch()
widget.show()

app.exec_()
