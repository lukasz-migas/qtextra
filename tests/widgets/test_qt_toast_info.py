"""Tests for toast info widgets."""

from __future__ import annotations

from qtpy.QtWidgets import QWidget

from qtextra.widgets.qt_toast_info import QtInfoToast, QtInfoToastManager, ToastPosition


def test_qt_info_toast_manager_make_returns_cached_manager():
    manager = QtInfoToastManager.make(ToastPosition.TOP_RIGHT)

    assert manager is QtInfoToastManager.make(ToastPosition.TOP_RIGHT)


def test_qt_info_toast_manager_removes_toast_when_closed(qtbot):
    parent = QWidget()
    parent.resize(400, 300)
    qtbot.addWidget(parent)

    toast = QtInfoToast("info", "Title", "Content", duration=-1, position=ToastPosition.NONE, parent=parent)
    manager = QtInfoToastManager.make(ToastPosition.TOP_RIGHT)

    manager.add(toast)

    assert toast in manager._toast[parent]

    toast.evt_closed.emit()

    assert toast not in manager._toast[parent]
