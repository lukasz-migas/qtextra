"""QtPanelToolbar with toggleable labels."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_toolbar_panel import QtPanelToolbar


def make_panel(title: str, body: str) -> QWidget:
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.addWidget(QLabel(f"<h2>{title}</h2>"))

    content = QLabel(body)
    content.setWordWrap(True)
    layout.addWidget(content)
    layout.addStretch()
    return panel


app = QApplication([])

window = QMainWindow()
window.setWindowTitle("QtPanelToolbar")
window.resize(900, 520)
THEMES.apply(window)

toolbar = QtPanelToolbar(window, label_hidden=False)
window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)

home_panel = make_panel("Home", "A compact labelled toolbar button can still drive a regular stacked panel.")
search_panel = make_panel("Search", "Toggle labels on and off to compare the compact and expanded toolbar layouts.")
settings_panel = make_panel("Settings", "Longer titles wrap within the toolbar column instead of widening the toolbar.")

toolbar.add_widget("home", title="Home", widget=home_panel, tooltip="Show the home panel.")
toolbar.add_widget("zoom", title="Search", widget=search_panel, tooltip="Show the search panel.")
toolbar.add_widget("gear", title="Settings", widget=settings_panel, tooltip="Show the settings panel.")

controls = QWidget()
controls_layout = QVBoxLayout(controls)

toggle_btn = QPushButton("Toggle Toolbar Labels")
toggle_btn.clicked.connect(lambda: setattr(toolbar, "label_hidden", not toolbar.label_hidden))
controls_layout.addWidget(toggle_btn)

info = QLabel("Use the button above to show or hide labels on the left toolbar.")
info.setWordWrap(True)
controls_layout.addWidget(info)
controls_layout.addWidget(toolbar.stack_widget)

window.setCentralWidget(controls)
window.show()

app.exec_()
