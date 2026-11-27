"""Open menu actions and plugin commands from a command palette."""

from functools import partial

from qtpy.QtWidgets import QApplication, QMainWindow, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_command_palette import QtCommandPalette

app = QApplication([])
window = QMainWindow()
window.setWindowTitle("Command palette")
THEMES.apply(window)

palette = QtCommandPalette.install(window)
panel = QWidget(window)
status = hp.make_label(panel, "Choose a command to run it.")
button = hp.make_btn(panel, "Commands", func=palette.open)
hp.make_v_layout(button, status, stretch_after=True, margin=16, spacing=12, parent=panel)
window.setCentralWidget(panel)

file_menu = window.menuBar().addMenu("&File")
hp.make_menu_item(window, "&Save report", "Ctrl+S", "save", file_menu, func=partial(status.setText, "Report saved."))
export_menu = hp.make_menu(window, "&Export", menu=file_menu)
hp.make_menu_item(
    window,
    "Export statistics",
    "Ctrl+Shift+E",
    "export",
    export_menu,
    func=partial(status.setText, "Statistics exported."),
)
palette.add_command(
    "Run analysis",
    partial(status.setText, "Analysis finished."),
    category="Statistics",
    icon="search",
    keywords=("ANOVA", "summary"),
)
palette.add_command("Reset view", partial(status.setText, "View reset."), category="View", icon="reset")

window.resize(700, 360)
window.show()
palette.open()
app.exec()
