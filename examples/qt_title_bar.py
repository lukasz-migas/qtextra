"""Example of an integrated (unified) title bar with custom widgets.

On macOS with Qt >= 6.9 the bar is drawn under the native title bar next to the window buttons.
Elsewhere it is shown as a normal row below the native frame.
"""

from qtpy.QtWidgets import QApplication, QMainWindow, QTextEdit, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_title_bar import QtTitleBar, enable_unified_title_bar

app = QApplication([])

window = QMainWindow()
window.setWindowTitle("Unified title bar")
window.resize(1000, 600)
unified = enable_unified_title_bar(window)

bar = QtTitleBar(window)
bar.add_widget(hp.make_qta_btn(bar, "list", tooltip="Toggle sidebar", size_preset="normal", checkable=True))
bar.add_widget(hp.make_qta_btn(bar, "update", tooltip="History", size_preset="normal"))
bar.add_widget(hp.make_qta_btn(bar, "chevron_left", tooltip="Back", size_preset="normal"))
bar.add_widget(hp.make_qta_btn(bar, "chevron_right", tooltip="Forward", size_preset="normal"))
bar.add_stretch()
bar.add_widget(hp.make_label(bar, "Update available", bold=True))
search = hp.make_line_edit(bar, placeholder="Type / to search")
search.setFixedWidth(240)
bar.add_widget(search)

central = QWidget(window)
layout = hp.make_v_layout(bar, margin=0, spacing=0, parent=central)
text = QTextEdit(central)
text.setPlainText(
    f"Unified title bar active: {unified}\n\n"
    "Drag empty areas of the bar (or the label) to move the window, double-click to zoom."
)
layout.addWidget(text, stretch=1)
window.setCentralWidget(central)

THEMES.apply(window)
window.show()
app.exec_()
