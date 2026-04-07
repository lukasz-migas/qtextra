"""QtProgressReport."""

from __future__ import annotations

from qtpy.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_progress_report import ProgressReportStep, ProgressStepStatus, QtProgressReport

STEP_DEFINITIONS = [
    ("Create account", "Set up your basic sign-in details."),
    ("Profile information", "Add the personal details needed for your workspace."),
    ("Business information", "Provide the organisation data used for billing and reporting."),
    ("Theme", "Choose the look and feel for your application."),
    ("Preview", "Review your configuration before continuing."),
]


class ProgressExampleController:
    """Drive the example widget through a simple step workflow."""

    def __init__(self, widget: QtProgressReport) -> None:
        """Initialize the controller."""
        self.widget = widget
        self.reset()

    def next_step(self) -> None:
        """Complete the current step and move to the next one."""
        current_index = self.widget.current_step_index()
        if current_index is None:
            return
        self.widget.set_step_status(current_index, ProgressStepStatus.COMPLETE, active=False)
        if current_index + 1 < len(self.widget.get_steps()):
            self.widget.set_step_status(current_index + 1, ProgressStepStatus.IN_PROGRESS, active=True)

    def fail_step(self) -> None:
        """Mark the current step as failed."""
        current_index = self.widget.current_step_index()
        if current_index is None:
            return
        self.widget.set_step_status(current_index, ProgressStepStatus.FAILED, active=True)

    def retry_step(self) -> None:
        """Return the current failed step to an in-progress state."""
        current_index = self.widget.current_step_index()
        if current_index is None:
            return
        self.widget.set_step_status(current_index, ProgressStepStatus.IN_PROGRESS, active=True)

    def reset(self) -> None:
        """Reset the example back to the first active step."""
        steps = []
        for index, (title, subtitle) in enumerate(STEP_DEFINITIONS):
            steps.append(
                ProgressReportStep(
                    title=title,
                    subtitle=subtitle,
                    status=ProgressStepStatus.IN_PROGRESS if index == 0 else ProgressStepStatus.PENDING,
                    active=index == 0,
                )
            )
        self.widget.set_steps(steps)


app = QApplication([])

window = QWidget()
layout = QVBoxLayout(window)
layout.setContentsMargins(16, 16, 16, 16)
layout.setSpacing(12)

progress_report = QtProgressReport()
controller = ProgressExampleController(progress_report)

layout.addWidget(progress_report)

button_row = QHBoxLayout()
button_row.setSpacing(8)

next_button = QPushButton("Complete current")
next_button.clicked.connect(controller.next_step)
button_row.addWidget(next_button)

fail_button = QPushButton("Fail current")
fail_button.clicked.connect(controller.fail_step)
button_row.addWidget(fail_button)

retry_button = QPushButton("Retry current")
retry_button.clicked.connect(controller.retry_step)
button_row.addWidget(retry_button)

reset_button = QPushButton("Reset")
reset_button.clicked.connect(controller.reset)
button_row.addWidget(reset_button)

layout.addLayout(button_row)

THEMES.apply(window)
window.resize(720, 480)
window.show()
app.exec_()
