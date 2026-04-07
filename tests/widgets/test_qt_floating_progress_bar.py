"""Tests for the floating progress bar overlay widget."""

from __future__ import annotations

from qtpy.QtCore import QPoint
from qtpy.QtWidgets import QDialog, QLabel, QPushButton, QWidget

from qtextra.widgets.qt_floating_progress_bar import QtFloatingProgressBar


def _floating_progress_host(qtbot) -> tuple[QWidget, QPushButton]:
    host = QWidget()
    host.resize(320, 200)
    target = QPushButton("Anchor", parent=host)
    target.resize(180, 42)
    target.move(70, 60)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host, target


def test_floating_progress_tracks_anchor_geometry(qtbot) -> None:
    host, target = _floating_progress_host(qtbot)
    overlay = QtFloatingProgressBar(parent=host, widget=target, text="Loading")
    qtbot.addWidget(overlay)

    initial_top_left = overlay.geometry().topLeft()
    target.move(target.x() + 25, target.y() + 12)
    qtbot.wait(50)

    assert overlay.widget() is target
    assert overlay.geometry().topLeft() != initial_top_left
    assert overlay.geometry().top() >= target.geometry().top() + overlay.Y_OFFSET


def test_floating_progress_text_and_value_updates(qtbot) -> None:
    host, target = _floating_progress_host(qtbot)
    overlay = QtFloatingProgressBar(parent=host, widget=target, text="Starting", minimum=0, maximum=10, value=2)
    qtbot.addWidget(overlay)

    overlay.set_text("Halfway there")
    overlay.set_value(5)

    assert overlay.text() == "Halfway there"
    assert overlay.value() == 5
    assert overlay.progress_bar.value() == 5


def test_floating_progress_hides_when_complete(qtbot) -> None:
    host, target = _floating_progress_host(qtbot)
    overlay = QtFloatingProgressBar(parent=host, widget=target, minimum=0, maximum=10, value=2)
    qtbot.addWidget(overlay)

    assert overlay.isVisible() is True

    overlay.set_value(10)

    assert overlay.value() == 10
    assert overlay.isVisible() is False


def test_floating_progress_reappears_when_progress_resumes(qtbot) -> None:
    host, target = _floating_progress_host(qtbot)
    overlay = QtFloatingProgressBar(parent=host, widget=target, minimum=0, maximum=10, value=10)
    qtbot.addWidget(overlay)

    assert overlay.isVisible() is False

    overlay.set_busy(True)
    assert overlay.isVisible() is True

    overlay.set_busy(False)
    overlay.set_value(4)

    assert overlay.isVisible() is True
    assert overlay.progress_bar.value() == 4


def test_floating_progress_busy_mode_round_trips_to_determinate(qtbot) -> None:
    host, target = _floating_progress_host(qtbot)
    overlay = QtFloatingProgressBar(parent=host, widget=target, minimum=2, maximum=8, value=4)
    qtbot.addWidget(overlay)

    overlay.set_busy(True)
    assert overlay.is_busy() is True
    assert overlay.progress_bar.minimum() == 0
    assert overlay.progress_bar.maximum() == 0

    overlay.set_range(3, 9)
    overlay.set_value(7)
    overlay.set_busy(False)

    assert overlay.is_busy() is False
    assert overlay.progress_bar.minimum() == 3
    assert overlay.progress_bar.maximum() == 9
    assert overlay.progress_bar.value() == 7


def test_floating_progress_reset_restores_minimum(qtbot) -> None:
    host, target = _floating_progress_host(qtbot)
    overlay = QtFloatingProgressBar(parent=host, widget=target, minimum=10, maximum=20, value=15, busy=True)
    qtbot.addWidget(overlay)

    overlay.reset()

    assert overlay.is_busy() is False
    assert overlay.value() == 10
    assert overlay.progress_bar.value() == 10


def test_floating_progress_hides_and_shows_with_anchor(qtbot) -> None:
    host, target = _floating_progress_host(qtbot)
    overlay = QtFloatingProgressBar(parent=host, widget=target, text="Loading")
    qtbot.addWidget(overlay)

    assert overlay.isVisible() is True

    target.hide()
    qtbot.wait(10)
    assert overlay.isVisible() is False

    target.show()
    qtbot.wait(10)
    assert overlay.isVisible() is True
    assert overlay.geometry().isValid() is True


def test_floating_progress_detaches_when_anchor_is_destroyed(qtbot) -> None:
    host = QWidget()
    host.resize(220, 140)
    target = QLabel("Anchor", parent=host)
    target.move(QPoint(40, 40))
    target.resize(120, 32)
    qtbot.addWidget(host)
    host.show()

    overlay = QtFloatingProgressBar(parent=host, widget=target, text="Loading")
    qtbot.addWidget(overlay)

    target.deleteLater()
    qtbot.wait(10)

    assert overlay.widget() is None
    assert overlay.isVisible() is False


def test_floating_progress_can_attach_to_top_level_dialog(qtbot) -> None:
    dialog = QDialog()
    dialog.resize(260, 140)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)

    overlay = QtFloatingProgressBar(widget=dialog, text="Working", value=30)
    qtbot.addWidget(overlay)

    assert overlay.parentWidget() is dialog
    assert overlay.widget() is dialog
    assert overlay.isVisible() is True
