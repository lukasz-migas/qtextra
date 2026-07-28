"""QtTutorial example."""

from __future__ import annotations

from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_tutorial import Position, QtTutorial, TutorialStep

app = QApplication([])

window = QWidget()
window.setWindowTitle("QtTutorial Example")
window.resize(760, 500)
THEMES.apply(window)

layout = QVBoxLayout(window)
layout.setContentsMargins(18, 18, 18, 18)
layout.setSpacing(12)

title_label = hp.make_label(window, "Export assistant", bold=True, font_size=20)
description_label = hp.make_label(
    window,
    "Configure an export, review its summary, and start the guided tutorial at any time.",
    wrap=True,
)
layout.addWidget(title_label)
layout.addWidget(description_label)

settings_group = QGroupBox("Export setup", window)
settings_layout = QFormLayout(settings_group)
settings_layout.setContentsMargins(14, 18, 14, 14)
settings_layout.setSpacing(10)

project_name = QLineEdit(settings_group)
project_name.setText("Quarterly analysis")
project_name.setPlaceholderText("Enter a project name")
settings_layout.addRow("Project name", project_name)

export_format = QComboBox(settings_group)
export_format.addItems(["PDF report", "CSV archive", "PNG images"])
settings_layout.addRow("Export format", export_format)

layout.addWidget(settings_group)

preview = QPlainTextEdit(window)
preview.setReadOnly(True)
preview.setMinimumHeight(150)
layout.addWidget(preview, stretch=True)

status_label = hp.make_label(window, "Ready to export.")
dim_background = QCheckBox("Dim the window during the tutorial", window)
dim_background.setChecked(True)
start_button = hp.make_btn(window, "Start tutorial", bold=True)
export_button = hp.make_btn(window, "Export", object_name="success_btn")

actions_layout = QHBoxLayout()
actions_layout.addWidget(dim_background)
actions_layout.addStretch(1)
actions_layout.addWidget(start_button)
actions_layout.addWidget(export_button)
layout.addLayout(actions_layout)
layout.addWidget(status_label)


def update_preview() -> None:
    """Update the export summary from the selected values."""
    preview.setPlainText(
        f"Project: {project_name.text() or 'Untitled project'}\n"
        f"Format: {export_format.currentText()}\n\n"
        "The exported files will include the current report, its figures, and metadata."
    )


def run_export() -> None:
    """Simulate exporting the configured project."""
    status_label.setText(f"Exported {project_name.text() or 'Untitled project'} as {export_format.currentText()}.")


tutorial: QtTutorial | None = None


def clear_tutorial(finished_tutorial: QtTutorial) -> None:
    """Release the finished tutorial instance."""
    global tutorial
    if tutorial is finished_tutorial:
        tutorial = None


def start_tutorial() -> None:
    """Start a guided tour of the export workflow."""
    global tutorial
    if tutorial is not None:
        tutorial.close()

    new_tutorial = QtTutorial(window, show_overlay=dim_background.isChecked())
    tutorial = new_tutorial
    new_tutorial.destroyed.connect(lambda *_args: clear_tutorial(new_tutorial))
    new_tutorial.set_steps(
        [
            TutorialStep(
                title="Name the project",
                message=(
                    "Give the export a recognizable name. The spotlight follows the target even when the window "
                    "moves or resizes."
                ),
                widget=project_name,
                position=Position.TOP,
                func=(project_name.setFocus,),
            ),
            TutorialStep(
                title="Choose a format",
                message="Select the output that best fits how you want to share or process the results.",
                widget=export_format,
                position=Position.RIGHT,
                func=(export_format.setFocus,),
            ),
            TutorialStep(
                title="Review the summary",
                message=(
                    "Each tutorial step can highlight a different widget. Use <b>Previous</b> and <b>Next</b>, "
                    "the arrow keys, or the P and N keys to navigate."
                ),
                widget=preview,
                position=Position.RIGHT_TOP,
            ),
            TutorialStep(
                title="Run the export",
                message="The overlay is mouse-transparent, so the highlighted controls remain interactive.",
                widget=export_button,
                position=Position.BOTTOM_RIGHT,
                func=(export_button.setFocus,),
            ),
        ]
    )
    new_tutorial.show()


project_name.textChanged.connect(update_preview)
export_format.currentTextChanged.connect(update_preview)
start_button.clicked.connect(start_tutorial)
export_button.clicked.connect(run_export)

update_preview()
window.show()
start_tutorial()

app.exec_()
