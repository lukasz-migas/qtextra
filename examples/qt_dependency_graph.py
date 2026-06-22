"""QtDependencyGraph."""

from __future__ import annotations

from itertools import cycle

from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_dependency_graph import QtDependencyGraph

STATE_COLORS = {
    "waiting": "#00C851",
    "processing": "#8E24AA",
    "complete": "#4285F4",
    "on_hold": "#e91e63",
}

NODES = [
    {
        "id": "prepare",
        "title": "Prepare inputs",
        "description": "Validate source files and initialize the workspace.",
        "state": "complete",
        "icon": "check",
    },
    {
        "id": "analyze",
        "title": "Analyze",
        "description": "Run the primary analysis.",
        "dependencies": ["prepare"],
        "state": "processing",
        "icon": "active",
    },
    {
        "id": "preview",
        "title": "Build preview",
        "description": "Generate a lightweight preview in parallel.",
        "dependencies": ["prepare"],
        "state": "waiting",
        "icon": "wait",
    },
    {
        "id": "publish",
        "title": "Publish results",
        "description": "Wait for both branches, then publish the completed result.",
        "dependencies": ["analyze", "preview"],
        "state": "waiting",
        "icon": "graph",
    },
    {
        "id": "cleanup",
        "title": "Cleanup cache",
        "description": "An independent maintenance task with no connections.",
        "state": "on_hold",
        "icon": "pause",
    },
]

app = QApplication([])
window = QWidget()
layout = QVBoxLayout(window)
graph = QtDependencyGraph(NODES, state_colors=STATE_COLORS)
layout.addWidget(graph)

buttons = QHBoxLayout()
orientation_button = QPushButton("Switch orientation")
buttons.addWidget(orientation_button)
zoom_out_button = QPushButton("Zoom out")
buttons.addWidget(zoom_out_button)
zoom_in_button = QPushButton("Zoom in")
buttons.addWidget(zoom_in_button)
reset_button = QPushButton("Reset zoom")
buttons.addWidget(reset_button)
fit_button = QPushButton("Fit graph")
buttons.addWidget(fit_button)
layout_button = QPushButton("Reset layout")
buttons.addWidget(layout_button)
lock_button = QPushButton("Lock nodes")
lock_button.setCheckable(True)
buttons.addWidget(lock_button)
layout.addLayout(buttons)


def switch_orientation() -> None:
    """Toggle between horizontal and vertical graph layouts."""
    graph.set_orientation("vertical" if graph.get_orientation() == "horizontal" else "horizontal")
    graph.fit_to_view()


def toggle_node_movement(locked: bool) -> None:
    """Lock or unlock direct node dragging."""
    graph.set_nodes_movable(not locked)
    lock_button.setText("Unlock nodes" if locked else "Lock nodes")


orientation_button.clicked.connect(switch_orientation)
zoom_out_button.clicked.connect(graph.zoom_out)
zoom_in_button.clicked.connect(graph.zoom_in)
reset_button.clicked.connect(graph.reset_zoom)
fit_button.clicked.connect(graph.fit_to_view)
layout_button.clicked.connect(graph.reset_layout)
lock_button.toggled.connect(toggle_node_movement)

preview_states = cycle(["waiting", "processing", "complete"])
timer = QTimer(window)
timer.setInterval(1500)
timer.timeout.connect(lambda: graph.set_node_state("preview", next(preview_states)))
timer.start()

THEMES.theme = "dark"
THEMES.apply(window)
window.resize(920, 560)
window.show()
app.exec_()
