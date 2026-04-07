"""Tests for the progress report widget."""

from __future__ import annotations

import pytest
from qtpy.QtWidgets import QLabel

from qtextra.widgets.qt_progress_report import ProgressReportStep, ProgressStepStatus, QtProgressReport


def test_progress_report_step_defaults():
    step = ProgressReportStep(title="Validate")

    assert step.subtitle == ""
    assert step.status == ProgressStepStatus.PENDING
    assert step.active is False


def test_progress_report_step_rejects_unknown_status():
    with pytest.raises(ValueError):
        ProgressReportStep(title="Validate", status="unknown")


def test_progress_report_accepts_dict_steps(qtbot):
    widget = QtProgressReport(
        steps=[
            {"title": "Create account", "status": "complete"},
            {"title": "Profile", "subtitle": "Current step", "status": "in_progress", "active": True},
            ProgressReportStep(title="Preview", status=ProgressStepStatus.PENDING),
        ]
    )
    qtbot.addWidget(widget)

    steps = widget.get_steps()

    assert [step.title for step in steps] == ["Create account", "Profile", "Preview"]
    assert steps[0].status == ProgressStepStatus.COMPLETE
    assert steps[1].active is True
    assert steps[2].status == ProgressStepStatus.PENDING


def test_progress_report_updates_active_step(qtbot):
    widget = QtProgressReport(
        steps=[
            ProgressReportStep(title="Create account", status=ProgressStepStatus.COMPLETE),
            ProgressReportStep(title="Profile", subtitle="Current step"),
            ProgressReportStep(title="Preview"),
        ]
    )
    qtbot.addWidget(widget)

    widget.set_active_step(1)

    steps = widget.get_steps()

    assert widget.current_step_index() == 1
    assert steps[1].active is True
    assert steps[1].status == ProgressStepStatus.IN_PROGRESS
    assert steps[0].active is False


def test_progress_report_uses_styled_child_widgets(qtbot):
    widget = QtProgressReport(
        steps=[
            ProgressReportStep(title="Create account", status=ProgressStepStatus.COMPLETE),
            ProgressReportStep(
                title="Profile",
                subtitle="Current step",
                status=ProgressStepStatus.IN_PROGRESS,
                active=True,
            ),
        ]
    )
    qtbot.addWidget(widget)

    title_labels = widget.findChildren(QLabel, "progressReportTitle")
    marker_labels = widget.findChildren(QLabel, "progressReportMarker")

    assert len(title_labels) == 2
    assert len(marker_labels) == 2
    assert title_labels[1].property("active") == "true"
    assert title_labels[1].property("status") == ProgressStepStatus.IN_PROGRESS.value
    assert marker_labels[0].text() == "✓"
    assert marker_labels[1].text() == "•"


def test_progress_report_size_hint_grows_with_content(qtbot):
    widget = QtProgressReport(
        steps=[
            ProgressReportStep(
                title="Long title for the currently active setup step",
                subtitle="A subtitle that should contribute to the height calculation.",
                status=ProgressStepStatus.IN_PROGRESS,
                active=True,
            ),
            ProgressReportStep(title="Done", status=ProgressStepStatus.COMPLETE),
        ]
    )
    qtbot.addWidget(widget)

    hint = widget.sizeHint()

    assert hint.width() >= 320
    assert hint.height() >= 120
    assert widget.minimumSizeHint().width() >= 260


def test_progress_report_renders_without_errors(qtbot):
    widget = QtProgressReport(
        steps=[
            ProgressReportStep(title="Complete", status=ProgressStepStatus.COMPLETE),
            ProgressReportStep(title="Failed", status=ProgressStepStatus.FAILED),
            ProgressReportStep(title="In progress", status=ProgressStepStatus.IN_PROGRESS, active=True),
            ProgressReportStep(title="Pending"),
        ]
    )
    widget.resize(420, 320)
    qtbot.addWidget(widget)

    widget.show()
    qtbot.waitExposed(widget)

    assert widget.grab().isNull() is False
