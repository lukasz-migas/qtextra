"""QtDependencyGraph."""

from __future__ import annotations

from itertools import cycle

from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.typing import TaskState
from qtextra.widgets.qt_dependency_graph import QtDependencyGraph

NODES = [
    {
        "id": "prepare",
        "title": "Prepare inputs",
        "description": "Validate source files and initialize the workspace.",
        "state": TaskState.FINISHED,
    },
    {
        "id": "analyze",
        "title": "Analyze",
        "description": "Run the primary analysis.",
        "dependencies": ["prepare"],
        "state": TaskState.RUNNING,
    },
    {
        "id": "preview",
        "title": "Build preview",
        "description": "Generate a lightweight preview in parallel.",
        "dependencies": ["prepare"],
    },
    {
        "id": "publish",
        "title": "Publish results",
        "description": "Wait for both branches, then publish the completed result.",
        "dependencies": ["analyze", "preview"],
    },
    {
        "id": "cleanup",
        "title": "Cleanup cache",
        "description": "An independent maintenance task with no connections.",
        "state": TaskState.PAUSED,
    },
]

app = QApplication([])
window = QWidget()
layout = QVBoxLayout(window)
graph = QtDependencyGraph(NODES)
layout.addWidget(graph)

buttons = QHBoxLayout()
orientation_button = QPushButton("Switch orientation")
buttons.addWidget(orientation_button)
fit_button = QPushButton("Fit graph")
buttons.addWidget(fit_button)
layout.addLayout(buttons)


def switch_orientation() -> None:
    """Toggle between horizontal and vertical graph layouts."""
    graph.set_orientation("vertical" if graph.get_orientation() == "horizontal" else "horizontal")
    graph.fit_to_view()


orientation_button.clicked.connect(switch_orientation)
fit_button.clicked.connect(graph.fit_to_view)

preview_states = cycle([TaskState.QUEUED, TaskState.RUNNING, TaskState.FINISHED])
timer = QTimer(window)
timer.setInterval(1500)
timer.timeout.connect(lambda: graph.set_node_state("preview", next(preview_states)))
timer.start()

THEMES.theme = "dark"
THEMES.apply(window)
window.resize(920, 560)
window.show()
app.exec_()
