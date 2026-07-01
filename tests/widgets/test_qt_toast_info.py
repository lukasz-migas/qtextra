"""Tests for toast info widgets."""

from __future__ import annotations

import typing as ty
from types import SimpleNamespace

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QDialog, QLineEdit, QMainWindow, QVBoxLayout, QWidget

import qtextra.helpers as hp
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


def test_notification_parent_prefers_owned_dialog(qtbot) -> None:
    """Visible owned dialogs should receive notifications before the main window."""
    main = QMainWindow()
    qtbot.addWidget(main)
    main.show()
    dialog = QDialog(main)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(10)

    assert hp.get_current_parent(main) is dialog


def test_make_notification_toast_is_child_overlay_and_restores_focus(monkeypatch, qtbot) -> None:
    """Focus-safe notifications should stay child widgets and restore focus."""
    dialog = QDialog()
    qtbot.addWidget(dialog)
    line_edit = QLineEdit(dialog)
    layout = QVBoxLayout(dialog)
    layout.addWidget(line_edit)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    line_edit.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.waitUntil(lambda: QApplication.focusWidget() is line_edit, timeout=1000)

    class _FakeToast(QWidget):
        """Small toast double that records normal QWidget state."""

        def __init__(
            self,
            *,
            icon: str,
            title: str,
            content: str,
            position: object,
            is_closable: bool,
            duration: int,
            parent: QWidget | None,
        ) -> None:
            super().__init__(parent)
            self.icon = icon
            self.title = title
            self.content = content
            self.position = position
            self.is_closable = is_closable
            self.duration = duration
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        @classmethod
        def new(
            cls,
            *,
            icon: str,
            title: str,
            content: str,
            position: object,
            is_closable: bool,
            duration: int,
            parent: QWidget | None,
            min_width: int = 0,
        ) -> _FakeToast:
            """Create a fake toast using the same class factory shape as QtInfoToast."""
            widget = cls(
                icon=icon,
                title=title,
                content=content,
                position=position,
                is_closable=is_closable,
                duration=duration,
                parent=parent,
            )
            if min_width > 0:
                widget.setMinimumWidth(min_width)
            return widget

    restored: list[tuple[QWidget | None, QWidget | None]] = []
    monkeypatch.setattr("qtextra.widgets.qt_toast_info.QtInfoToast", _FakeToast)
    monkeypatch.setattr(hp, "restore_focus", lambda window, focus: restored.append((window, focus)))

    toast = hp._make_notification_toast(
        dialog,
        title="Title",
        message="Message",
        icon="info",
        position="top_left",
        is_closable=True,
    )
    qtbot.waitUntil(lambda: bool(restored), timeout=1000)

    assert toast.parent() is dialog
    assert not toast.isWindow()
    assert toast.position == ToastPosition.TOP_LEFT
    assert toast.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert toast.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert restored[0] == (dialog, line_edit)


def test_restore_notification_focus_ignores_deleted_widgets() -> None:
    """Deleted Qt wrappers should not make focus restoration raise."""

    class _DeletedWidget:
        """Widget double that behaves like a deleted Qt wrapper."""

        def isVisible(self) -> bool:
            """Raise like PyQt/PySide wrappers after the C++ object is deleted."""
            raise RuntimeError("wrapped object has been deleted")

    deleted = ty.cast(QWidget, _DeletedWidget())

    hp.restore_focus(deleted, deleted)


def test_restore_notification_focus_reactivates_target_window(monkeypatch) -> None:
    """Focus restoration should reactivate the notification window when needed."""

    class _Window:
        """Window double that tracks activation calls."""

        activated = False
        raised = False

        def isVisible(self) -> bool:
            """Return visible state."""
            return True

        def activateWindow(self) -> None:
            """Record activation attempts."""
            self.activated = True

        def raise_(self) -> None:
            """Record raise attempts."""
            self.raised = True

    class _FocusWidget:
        """Focus widget double bound to a window."""

        focused = False

        def __init__(self, window: _Window) -> None:
            self._window = window

        def isVisible(self) -> bool:
            """Return visible state."""
            return True

        def window(self) -> _Window:
            """Return the owning window."""
            return self._window

        def setFocus(self, _reason: Qt.FocusReason) -> None:
            """Record focus attempts."""
            self.focused = True

    window = _Window()
    focus_widget = _FocusWidget(window)
    app = SimpleNamespace(activeWindow=lambda: object())
    fake_qw = SimpleNamespace(QApplication=SimpleNamespace(instance=lambda: app))
    monkeypatch.setattr(hp, "Qw", fake_qw)

    hp.restore_focus(ty.cast(QWidget, window), ty.cast(QWidget, focus_widget))

    assert window.activated
    assert window.raised
    assert focus_widget.focused
