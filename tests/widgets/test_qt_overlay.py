"""Tests for overlay widgets."""

from __future__ import annotations

from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from qtextra.widgets.qt_overlay import QtOverlayDismissMessage, QtOverlayLabel, QtOverlayMessage


def _overlay_host(qtbot):
    host = QWidget()
    host.resize(280, 180)
    layout = QVBoxLayout(host)
    target = QPushButton("Anchor")
    target.resize(160, 50)
    layout.addStretch(1)
    layout.addWidget(target, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addStretch(1)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host, target


def test_overlay_label_tracks_anchor_geometry(qtbot):
    host, target = _overlay_host(qtbot)
    overlay = QtOverlayLabel(parent=host, text="Overlay", widget=target)
    qtbot.addWidget(overlay)

    initial_top_left = overlay.geometry().topLeft()
    target.move(target.x() + 20, target.y() + 10)
    qtbot.wait(10)

    assert overlay.widget() is target
    assert overlay.geometry().topLeft() != initial_top_left
    assert overlay.geometry().top() >= target.geometry().top() + overlay.Y_OFFSET


def test_overlay_label_hides_and_shows_with_anchor(qtbot):
    host, target = _overlay_host(qtbot)
    overlay = QtOverlayLabel(parent=host, text="Overlay", widget=target)
    qtbot.addWidget(overlay)

    assert overlay.isVisible() is True

    target.hide()
    qtbot.wait(10)
    assert overlay.isVisible() is False

    target.show()
    qtbot.wait(10)
    assert overlay.isVisible() is True
    assert overlay.geometry().isValid() is True

    host.close()


def test_overlay_message_reject_button_emits_signal(qtbot):
    host, target = _overlay_host(qtbot)
    overlay = QtOverlayDismissMessage(parent=host, widget=target, text="Close me")
    qtbot.addWidget(overlay)
    overlay._msg_widget.set_buttons(cancel_btn=True)

    with qtbot.waitSignal(overlay.evt_rejected, timeout=500):
        qtbot.mouseClick(overlay._msg_widget.cancel_btn, Qt.MouseButton.LeftButton)

    assert overlay.is_displayed is False


def test_overlay_message_dismiss_persists_when_enabled(qtbot):
    host, target = _overlay_host(qtbot)
    overlay = QtOverlayDismissMessage(parent=host, widget=target, text="Dismiss me", dismiss_btn=True, can_dismiss=True)
    qtbot.addWidget(overlay)

    with qtbot.waitSignal(overlay.evt_dismissed, timeout=500):
        qtbot.mouseClick(overlay._msg_widget.dismiss_btn, Qt.MouseButton.LeftButton)

    overlay.display()

    assert overlay.is_dismissed is True
    assert overlay.is_displayed is False


def test_overlay_message_can_be_redisplayed_when_non_persistent(qtbot):
    host, target = _overlay_host(qtbot)
    overlay = QtOverlayMessage(parent=host, widget=target, text="Temporary", can_dismiss=False)
    qtbot.addWidget(overlay)

    overlay.dismiss()
    assert overlay.is_dismissed is False

    overlay.display()

    assert overlay.is_displayed is True


def test_overlay_detaches_when_anchor_is_destroyed(qtbot):
    host = QWidget()
    host.resize(200, 120)
    target = QLabel("Anchor", parent=host)
    target.move(QPoint(30, 30))
    target.resize(120, 40)
    qtbot.addWidget(host)
    host.show()

    overlay = QtOverlayLabel(parent=host, text="Overlay", widget=target)
    qtbot.addWidget(overlay)

    target.deleteLater()
    qtbot.wait(10)

    assert overlay.widget() is None
    assert overlay.isVisible() is False
