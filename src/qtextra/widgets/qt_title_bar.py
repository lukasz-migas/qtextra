"""Integrated (unified) title bar for top-level windows.

On macOS with Qt >= 6.9 the window content can extend under the native title bar while the native
window buttons (close/minimize/zoom) are kept. ``QtTitleBar`` is a plain widget row that is meant to sit
at the very top of the window and host arbitrary widgets (buttons, search fields, labels, ...).

On other platforms (or older Qt) ``enable_unified_title_bar`` does nothing and ``QtTitleBar`` behaves like
a normal toolbar row below the native frame.
"""

from __future__ import annotations

import sys

from qtpy.QtCore import QEvent, QObject, Qt
from qtpy.QtGui import QMouseEvent, QShowEvent
from qtpy.QtWidgets import QHBoxLayout, QWidget

import qtextra.helpers as hp

_EXPANDED_HINT = getattr(Qt.WindowType, "ExpandedClientAreaHint", None)
_NO_BACKGROUND_HINT = getattr(Qt.WindowType, "NoTitleBarBackgroundHint", None)
_RESPECTS_SAFE_AREA = getattr(Qt.WidgetAttribute, "WA_ContentsMarginsRespectsSafeArea", None)


def supports_unified_title_bar() -> bool:
    """Return True if the current platform and Qt version support an integrated title bar."""
    return sys.platform == "darwin" and _EXPANDED_HINT is not None and _NO_BACKGROUND_HINT is not None


def enable_unified_title_bar(window: QWidget) -> bool:
    """Extend the window content under the native title bar.

    Call this before the window is shown.

    Parameters
    ----------
    window : QWidget
        Top-level window (usually a ``QMainWindow``).

    Returns
    -------
    bool
        True if the window flags were applied, False if unsupported (window left untouched).
    """
    if not supports_unified_title_bar():
        return False
    window.setWindowFlag(_EXPANDED_HINT, True)
    window.setWindowFlag(_NO_BACKGROUND_HINT, True)
    _hide_native_title(window)
    return True


def _hide_native_title(window: QWidget) -> None:
    """Hide the title text drawn by macOS in the title bar (Qt has no flag for it).

    Calls ``[[view window] setTitleVisibility:NSWindowTitleHidden]`` through the Objective-C runtime.
    """
    import ctypes
    import ctypes.util

    libobjc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    libobjc.sel_registerName.restype = ctypes.c_void_p
    libobjc.sel_registerName.argtypes = [ctypes.c_char_p]
    send_ptr = ctypes.cast(libobjc.objc_msgSend, ctypes.c_void_p).value
    get_window = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(send_ptr)
    set_long = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)(send_ptr)

    view = int(window.winId())  # creates the native window (NSView) if needed
    ns_window = get_window(view, libobjc.sel_registerName(b"window"))
    if ns_window:
        set_long(ns_window, libobjc.sel_registerName(b"setTitleVisibility:"), 1)  # NSWindowTitleHidden


def is_unified_title_bar(window: QWidget) -> bool:
    """Return True if the window content extends under the native title bar."""
    if _EXPANDED_HINT is None:
        return False
    return bool(window.windowFlags() & _EXPANDED_HINT)


class QtTitleBar(QWidget):
    """Widget row that acts as the window title bar.

    Empty areas (and widgets that ignore mouse presses, e.g. labels) can be used to drag the window, and
    double-clicking them toggles the maximized state. When the window uses the unified title bar, space on
    the left is reserved for the native window buttons (except in full screen, where they are hidden).

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget.
    height : int
        Fixed height of the bar.
    button_inset : int
        Space reserved on the left for the native window buttons in unified mode.
    spacing : int
        Spacing between widgets.
    margin : int
        Left/right margin (added to the inset) of the bar.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        height: int = 38,
        button_inset: int = 78,
        spacing: int = 4,
        margin: int = 6,
    ) -> None:
        super().__init__(parent)
        self.button_inset = button_inset
        self._margin = margin
        self._watched: QWidget | None = None

        self.setFixedHeight(height)
        self._layout: QHBoxLayout = hp.make_h_layout(spacing=spacing, margin=(margin, 0, margin, 0), parent=self)

    def add_widget(self, widget: QWidget, stretch: int = 0) -> QWidget:
        """Add widget to the bar."""
        self._layout.addWidget(widget, stretch)
        return widget

    def add_stretch(self, stretch: int = 1) -> None:
        """Add stretch to the bar."""
        self._layout.addStretch(stretch)

    def add_spacing(self, size: int) -> None:
        """Add fixed spacing to the bar."""
        self._layout.addSpacing(size)

    @property
    def left_inset(self) -> int:
        """Space currently reserved on the left for the native window buttons."""
        window = self.window()
        if window is self or not is_unified_title_bar(window) or window.isFullScreen():
            return 0
        return self.button_inset

    def update_inset(self) -> None:
        """Update the left margin to match the current window state."""
        self._layout.setContentsMargins(self._margin + self.left_inset, 0, self._margin, 0)

    def showEvent(self, event: QShowEvent) -> None:
        """Watch the top-level window for state changes and update the inset."""
        window = self.window()
        if window is not self._watched:
            if self._watched is not None:
                self._watched.removeEventFilter(self)
            window.installEventFilter(self)
            self._watched = window
        if is_unified_title_bar(window):
            self._ignore_safe_area()
        self.update_inset()
        super().showEvent(event)

    def _ignore_safe_area(self) -> None:
        """Stop the bar and its ancestors from reserving the title bar area (safe-area margins)."""
        if _RESPECTS_SAFE_AREA is None:
            return
        widget: QWidget | None = self
        while widget is not None:
            widget.setAttribute(_RESPECTS_SAFE_AREA, False)
            widget = None if widget.isWindow() else widget.parentWidget()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Update the inset when the window enters/leaves full screen."""
        if obj is self._watched and event.type() == QEvent.Type.WindowStateChange:
            self.update_inset()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start a native window move when pressing on an empty area."""
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Toggle maximized state when double-clicking an empty area."""
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            if not window.isFullScreen():
                window.showNormal() if window.isMaximized() else window.showMaximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
